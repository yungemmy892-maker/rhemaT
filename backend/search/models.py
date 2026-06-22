import datetime
import uuid

import mongoengine as me


def _gen_id():
    return uuid.uuid4().hex


class SearchHistory(me.Document):
    """One row per identification attempt. Powers Home's 'Recent searches'
    and Library's 'History' tab, and the Profile 'Identified' counter."""

    id = me.StringField(primary_key=True, default=_gen_id)
    user_id = me.StringField(required=True)
    query = me.StringField(required=True)
    verse_id = me.StringField()  # matches Verse.to_dict()["id"], blank if no match
    version = me.StringField(choices=("KJV", "WEB"), default="KJV")
    matched = me.BooleanField(default=True)
    confidence = me.FloatField(default=0.0)
    created_at = me.DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "search_history",
        "indexes": ["user_id", "-created_at"],
        "ordering": ["-created_at"],
    }

    def to_dict(self):
        return {
            "id": str(self.id),
            "query": self.query,
            "verseId": self.verse_id,
            "matched": self.matched,
            "confidence": self.confidence,
            "timestamp": int(self.created_at.replace(tzinfo=datetime.timezone.utc).timestamp() * 1000),
        }
