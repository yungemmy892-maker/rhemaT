from rest_framework import serializers

from bible.models import SUPPORTED_VERSIONS


class SaveVerseSerializer(serializers.Serializer):
    verse_id = serializers.CharField()
    version = serializers.ChoiceField(
        choices=list(SUPPORTED_VERSIONS), required=False, allow_null=True
    )


class SettingsUpdateSerializer(serializers.Serializer):
    notifications = serializers.BooleanField(required=False)
    darkMode = serializers.BooleanField(required=False)
    quietHours = serializers.BooleanField(required=False)
    dailyVerse = serializers.BooleanField(required=False)
    verseReminders = serializers.BooleanField(required=False)
    savedActivity = serializers.BooleanField(required=False)
    community = serializers.BooleanField(required=False)
    productUpdates = serializers.BooleanField(required=False)
    sound = serializers.BooleanField(required=False)
    dailyVerseTime = serializers.ChoiceField(
        choices=["Morning", "Midday", "Evening"], required=False
    )
    bibleVersion = serializers.ChoiceField(choices=list(SUPPORTED_VERSIONS), required=False)
    language = serializers.CharField(required=False)
    theme = serializers.CharField(required=False)
