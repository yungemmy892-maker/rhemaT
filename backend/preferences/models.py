import datetime
import uuid

import mongoengine as me


def _gen_id():
    return uuid.uuid4().hex


class SavedVerse(me.Document):
    """Backs Library's 'Saved' tab and Profile's saved counter."""

    id = me.StringField(primary_key=True, default=_gen_id)
    user_id = me.StringField(required=True)
    verse_id = me.StringField(required=True)  # e.g. "john-3-16", matches Verse.to_dict()["id"]
    version = me.StringField(choices=("KJV", "WEB"), default="KJV")
    created_at = me.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "saved_verses",
        "indexes": [
            {"fields": ["user_id", "verse_id"], "unique": True},
            "user_id",
        ],
        "ordering": ["-created_at"],
    }


# Fixed set matching the existing Library "Collections" tab UI, which
# hardcodes exactly these four named tiles. Verses are auto-tagged into
# these via COLLECTION_TAGS below so the tab shows real, meaningful data
# instead of an empty state, without adding any new UI for users to create
# custom collections (none exists in the current design).
COLLECTION_NAMES = ["Comfort", "Strength", "Gratitude", "Prayer"]

COLLECTION_TAGS = {
    "Comfort": ["matthew-11-28", "psalms-23-1", "psalms-46-10"],
    "Strength": ["philippians-4-13", "isaiah-40-31"],
    "Gratitude": ["1corinthians-13-4", "romans-8-28"],
    "Prayer": ["jeremiah-29-11", "proverbs-3-5", "john-3-16"],
}


class UserSettings(me.Document):
    """One document per user, backing the Settings screen toggles."""

    id = me.StringField(primary_key=True, default=_gen_id)
    user_id = me.StringField(required=True, unique=True)

    notifications = me.BooleanField(default=True)
    dark_mode = me.BooleanField(default=False)
    quiet_hours = me.BooleanField(default=False)

    daily_verse = me.BooleanField(default=True)
    verse_reminders = me.BooleanField(default=True)
    saved_activity = me.BooleanField(default=False)
    community = me.BooleanField(default=False)
    product_updates = me.BooleanField(default=True)
    sound = me.BooleanField(default=True)
    daily_verse_time = me.StringField(
        choices=("Morning", "Midday", "Evening"), default="Morning"
    )

    bible_version = me.StringField(choices=("KJV", "WEB"), default="KJV")
    language = me.StringField(default="English")
    theme = me.StringField(default="Calm Lavender")
    ai_voice = me.StringField(default="Soft · Female")
    voice_tone = me.StringField(default="Gentle")

    meta = {"collection": "user_settings", "indexes": ["user_id"]}

    def to_dict(self):
        return {
            "notifications": self.notifications,
            "darkMode": self.dark_mode,
            "quietHours": self.quiet_hours,
            "dailyVerse": self.daily_verse,
            "verseReminders": self.verse_reminders,
            "savedActivity": self.saved_activity,
            "community": self.community,
            "productUpdates": self.product_updates,
            "sound": self.sound,
            "dailyVerseTime": self.daily_verse_time,
            "bibleVersion": self.bible_version,
            "language": self.language,
            "theme": self.theme,
            "aiVoice": self.ai_voice,
            "voiceTone": self.voice_tone,
        }
