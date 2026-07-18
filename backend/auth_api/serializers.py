from rest_framework import serializers


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField(
        help_text="The Google Identity Services credential/ID token from the frontend."
    )


class EmailRegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, allow_blank=True, required=False)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=6, max_length=128, write_only=True)


class EmailLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)
    new_password = serializers.CharField(min_length=6, max_length=128)


class UpdateProfileSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, allow_blank=False, required=False)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(required=False, allow_blank=True)
    new_password = serializers.CharField(min_length=6, max_length=128)