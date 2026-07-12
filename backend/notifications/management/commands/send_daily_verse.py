"""
Sends the daily "verse of the day" notification — via push AND email at the
same time, not one as a fallback for the other — to every user whose chosen
delivery time (Morning / Midday / Evening) falls in the current UTC hour.

Runs automatically in-process (see notifications/scheduler.py, started from
NotificationsConfig.ready()) every 15 minutes, so no external cron setup is
required for a typical single-process deployment. Set
DISABLE_INPROCESS_SCHEDULER=true and wire this command into a real
scheduler (cron, Render Cron Jobs, etc.) instead for multi-worker
deployments, where every worker process would otherwise start its own
in-process timer and could double-send under rare race conditions.

Can still be run by hand:

    python manage.py send_daily_verse
    python manage.py send_daily_verse --force   # ignore time windows + dedupe, for testing

Each user receives at most ONE notification per calendar day (UTC). The
command tracks this in UserSettings.last_daily_sent_date, so re-runs of
the cron within the same hour don't duplicate delivery.

Delivery windows (WAT = UTC+1):
    Morning  → 07:00–07:59 WAT  (06:xx UTC)
    Midday   → 12:00–12:59 WAT  (11:xx UTC)
    Evening  → 19:00–19:59 WAT  (18:xx UTC)
"""
import datetime

from django.core.management.base import BaseCommand

from bible.models import Verse
from bible.views import POPULAR_REFS
from notifications.email import send_daily_verse_email
from notifications.models import Notification, PushSubscription
from notifications.push import send_push_to_user
from preferences.models import UserSettings
from users.models import User

# UTC hour → WAT label mapping
# WAT is UTC+1, so 06:xx UTC = 07:xx WAT (Morning), etc.
DELIVERY_WINDOWS = {
    "Morning": 6,    # 06:xx UTC = 07:xx WAT
    "Midday":  11,   # 11:xx UTC = 12:xx WAT
    "Evening": 18,   # 18:xx UTC = 19:xx WAT
}


class Command(BaseCommand):
    help = (
        "Sends the daily verse notification to users whose chosen time window "
        "matches the current UTC hour. Run every 15 minutes via cron."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Ignore time windows and last-sent date — send to ALL users "
                "with daily_verse=True. Useful for testing."
            ),
        )

    def handle(self, *args, **options):
        now_utc = datetime.datetime.utcnow()
        today = now_utc.date()
        current_hour = now_utc.hour
        force = options["force"]

        # Determine which time labels are currently in their delivery window
        active_times = {
            label
            for label, utc_hour in DELIVERY_WINDOWS.items()
            if force or current_hour == utc_hour
        }

        if not active_times and not force:
            self.stdout.write(
                f"UTC {now_utc.strftime('%H:%M')} — no delivery window active. Exiting."
            )
            return

        self.stdout.write(
            f"UTC {now_utc.strftime('%H:%M')} — active windows: {active_times}"
        )

        # Today's verse (same for everyone on the same day)
        day_index = today.day % len(POPULAR_REFS)
        book, chapter, verse_num = POPULAR_REFS[day_index]

        sent_push = 0
        sent_email = 0
        skipped = 0
        failed = 0

        for settings_doc in UserSettings.objects(
            daily_verse=True,
            daily_verse_time__in=list(active_times),
        ):
            # Already sent today → skip
            if not force and settings_doc.last_daily_sent_date == today:
                skipped += 1
                continue

            # M5: atomically claim today's send slot for this user before
            # doing any work. A plain check-then-write (the old behavior)
            # lets two workers both pass the "not sent today" check before
            # either writes, causing a double-send under multi-worker
            # deployment. This conditional update only succeeds for
            # whichever worker gets there first — `last_daily_sent_date__ne`
            # means the update only matches (and modifies) a document that
            # still needs today's send, so a losing worker's update simply
            # matches zero documents instead of racing.
            if not force:
                claimed = UserSettings.objects(
                    id=settings_doc.id, last_daily_sent_date__ne=today
                ).update(set__last_daily_sent_date=today)
                if not claimed:
                    skipped += 1
                    continue

            user = User.objects(id=settings_doc.user_id).first()
            if user is None:
                skipped += 1
                continue

            # Respect the master notifications toggle
            if not settings_doc.notifications:
                skipped += 1
                continue

            # Resolve verse in user's preferred version, fall back to KJV
            version = settings_doc.bible_version or "KJV"
            verse = Verse.objects(
                book=book, chapter=chapter, verse=verse_num, version=version
            ).first()
            if verse is None:
                verse = Verse.objects(
                    book=book, chapter=chapter, verse=verse_num, version="KJV"
                ).first()
            if verse is None:
                self.stderr.write(f"Verse not found for {user.email} — skipping.")
                skipped += 1
                continue

            # Create in-app notification record
            Notification(
                user_id=str(user.id),
                kind="verse_of_day",
                title="Verse of the day",
                body=f"\u201c{verse.text}\u201d \u2014 {verse.ref}",
            ).save()

            # Deliver via BOTH channels every time — not push-with-email-
            # fallback. A push notification is easy to miss/dismiss without
            # reading, so the email is the durable copy, and vice versa.
            has_push = PushSubscription.objects(user_id=str(user.id)).count() > 0

            try:
                if has_push:
                    result = send_push_to_user(
                        str(user.id),
                        {
                            "title": "Verse of the day",
                            "body": f"{verse.ref} \u2014 tap to read",
                            "url": "/app/home",
                        },
                    )
                    if result.get("sent", 0) > 0:
                        sent_push += 1

                send_daily_verse_email(
                    user.email, user.name, verse.ref, verse.text, verse.version
                )
                sent_email += 1

            except Exception as exc:  # noqa: BLE001
                failed += 1
                self.stderr.write(
                    self.style.WARNING(f"Failed to notify {user.email}: {exc}")
                )
                # Release the claim so a later run can retry this user
                # instead of silently skipping them for the rest of today.
                if not force:
                    UserSettings.objects(id=settings_doc.id).update(
                        unset__last_daily_sent_date=1
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done — push={sent_push} email={sent_email} "
                f"skipped={skipped} failed={failed}"
            )
        )