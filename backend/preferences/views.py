from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from bible.models import resolve_verse
from notifications.models import Notification
from users.models import User

from .models import COLLECTION_NAMES, COLLECTION_TAGS, SavedVerse, UserSettings
from .serializers import SaveVerseSerializer, SettingsUpdateSerializer


def _field_map():
    """camelCase API field -> snake_case document field."""
    return {
        "notifications": "notifications",
        "darkMode": "dark_mode",
        "quietHours": "quiet_hours",
        "dailyVerse": "daily_verse",
        "verseReminders": "verse_reminders",
        "savedActivity": "saved_activity",
        "community": "community",
        "productUpdates": "product_updates",
        "sound": "sound",
        "dailyVerseTime": "daily_verse_time",
        "bibleVersion": "bible_version",
        "language": "language",
        "theme": "theme",
        "aiVoice": "ai_voice",
        "voiceTone": "voice_tone",
    }


class SavedVersesView(APIView):
    """
    GET  /api/v1/preferences/saved/      -> list of resolved Verse dicts
    POST /api/v1/preferences/saved/      -> { verse_id, version? } toggles save state
    """

    def get(self, request):
        rows = SavedVerse.objects(user_id=str(request.user.id))
        # Resolve to full verse dicts (in whichever version each verse was
        # originally saved from) so Library doesn't need a second
        # round-trip per verse, matching how BIBLE_VERSES.find() worked
        # client-side before.
        verses = []
        for row in rows:
            v = resolve_verse(row.verse_id, row.version)
            if v:
                verses.append(v.to_dict())
        return Response(verses)

    def post(self, request):
        serializer = SaveVerseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verse_id = serializer.validated_data["verse_id"]
        version = serializer.validated_data.get("version") or "KJV"
        user_id = str(request.user.id)

        existing = SavedVerse.objects(user_id=user_id, verse_id=verse_id).first()
        if existing:
            existing.delete()
            saved = False
        else:
            SavedVerse(user_id=user_id, verse_id=verse_id, version=version).save()
            saved = True

        count = SavedVerse.objects(user_id=user_id).count()
        User.objects(id=user_id).update(set__saved_count=count)

        if saved:
            settings_doc = UserSettings.objects(user_id=user_id).first()
            if settings_doc is None or settings_doc.saved_activity:
                verse = resolve_verse(verse_id, version)
                if verse:
                    Notification(
                        user_id=user_id,
                        kind="saved_to_library",
                        title="Saved to your library",
                        body=f"{verse.ref} was added to your saved verses.",
                    ).save()

        return Response({"verseId": verse_id, "saved": saved}, status=status.HTTP_200_OK)


class CollectionsView(APIView):
    """GET /api/v1/preferences/collections/ — the 4 fixed themed tiles."""

    def get(self, request):
        results = []
        for name in COLLECTION_NAMES:
            verse_ids = COLLECTION_TAGS.get(name, [])
            results.append({"name": name, "count": len(verse_ids), "verseIds": verse_ids})
        return Response(results)


class SettingsView(APIView):
    """
    GET   /api/v1/preferences/settings/  -> current settings
    PATCH /api/v1/preferences/settings/  -> partial update of any toggle
    """

    def get(self, request):
        settings_doc = UserSettings.objects(user_id=str(request.user.id)).first()
        if settings_doc is None:
            settings_doc = UserSettings(user_id=str(request.user.id)).save()
        return Response(settings_doc.to_dict())

    def patch(self, request):
        serializer = SettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = str(request.user.id)
        settings_doc = UserSettings.objects(user_id=user_id).first()
        if settings_doc is None:
            settings_doc = UserSettings(user_id=user_id)

        field_map = _field_map()
        for api_field, value in serializer.validated_data.items():
            setattr(settings_doc, field_map[api_field], value)
        settings_doc.save()

        return Response(settings_doc.to_dict())
