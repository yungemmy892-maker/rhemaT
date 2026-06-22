from rest_framework import serializers


class VerseRefQuerySerializer(serializers.Serializer):
    book = serializers.CharField()
    chapter = serializers.IntegerField()
    verse = serializers.IntegerField()
