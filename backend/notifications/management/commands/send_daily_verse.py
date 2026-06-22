"""
Sends the daily "verse of the day" notification to every user who has it
enabled in Settings (UserSettings.daily_verse). Intended to be run once a
day by an external scheduler (cron, systemd timer, Celery beat, etc.) —
see README "Daily notifications" section for exact setup.

Delivery: tries Web Push first (instant, works even if the app/tab is
closed, matches "push if supported"); if the user has no active push
subscription at all, falls back to email instead, per the agreed
"push if supported, email as fallback" behavior.
"""
import datetime

from django.core.management.base import BaseCommand

from bible.views import POPULAR_REFS
from bible.models import Verse
from notifications.email import send_daily_verse_email
from notifications.models import Notification, PushSubscription
from notifications.push import send_push_to_user
from preferences.models import UserSettings
from users.models import User


class Command(BaseCommand):
    help = "Sends the daily verse-of-the-day notification (push, falling back to email)."

    def handle(self, *args, **options):
        day_index = datetime.date.today().day % len(POPULAR_REFS)
        book, chapter, verse_num = POPULAR_REFS[day_index]

        sent_push = 0
        sent_email = 0
        skipped = 0
        failed = 0

        for settings_doc in UserSettings.objects(daily_verse=True):
            user = User.objects(id=settings_doc.user_id).first()
            if user is None:
                continue

            version = settings_doc.bible_version or "KJV"
            verse = Verse.objects(book=book, chapter=chapter, verse=verse_num, version=version).first()
            if verse is None:
                verse = Verse.objects(book=book, chapter=chapter, verse=verse_num, version="KJV").first()
            if verse is None:
                skipped += 1
                continue

            Notification(
                user_id=str(user.id),
                kind="verse_of_day",
                title="Verse of the day",
                body=f"\u201c{verse.text}\u201d \u2014 {verse.ref}",
            ).save()

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
                    else:
                        # All subscriptions were expired/invalid — fall back.
                        send_daily_verse_email(user.email, user.name, verse.ref, verse.text, verse.version)
                        sent_email += 1
                else:
                    send_daily_verse_email(user.email, user.name, verse.ref, verse.text, verse.version)
                    sent_email += 1
            except Exception as exc:  # noqa: BLE001 — log and continue the batch
                failed += 1
                self.stderr.write(self.style.WARNING(f"Failed to notify {user.email}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. push={sent_push} email={sent_email} skipped={skipped} failed={failed}"
            )
        )
