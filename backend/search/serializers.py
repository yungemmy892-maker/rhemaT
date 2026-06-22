from rest_framework import serializers

from bible.models import SUPPORTED_VERSIONS


class IdentifySerializer(serializers.Serializer):
    query = serializers.CharField(max_length=500, allow_blank=False)
    version = serializers.ChoiceField(
        choices=list(SUPPORTED_VERSIONS), required=False, allow_null=True
    )
