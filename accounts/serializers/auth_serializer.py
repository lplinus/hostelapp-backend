from rest_framework import serializers
from django.contrib.auth import authenticate
from accounts.models import User


class RegisterSerializer(serializers.Serializer):
    """Validates registration data without exposing the model directly."""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(
        max_length=150, required=False, default="", allow_blank=True
    )
    last_name = serializers.CharField(
        max_length=150, required=False, default="", allow_blank=True
    )
    phone = serializers.CharField(
        max_length=20, required=False, default="", allow_blank=True
    )
    role = serializers.ChoiceField(
        choices=User.ROLE_CHOICES, default="guest", required=False
    )

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        return attrs


class LoginSerializer(serializers.Serializer):
    """Validates login credentials — supports email or username."""

    username = serializers.CharField()  # accepts username or email
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username_or_email = attrs.get("username")
        password = attrs.get("password")

        # Allow login with email
        if "@" in username_or_email:
            try:
                user_obj = User.objects.get(email=username_or_email)
                username_or_email = user_obj.username
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {"detail": "Invalid credentials. Please try again."}
                )

        user = authenticate(username=username_or_email, password=password)

        if user is None:
            raise serializers.ValidationError(
                {"detail": "Invalid credentials. Please try again."}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "This account has been deactivated."}
            )

        attrs["user"] = user
        return attrs


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)


class SendOTPSerializer(serializers.Serializer):
    # Only for authenticated users updating their profile
    pass


class VerifyOTPSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)
