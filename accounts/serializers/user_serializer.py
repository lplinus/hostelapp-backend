from rest_framework import serializers
from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    """Full user serializer — used by admin endpoints."""

    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {
            "password": {"write_only": True},
        }


class UserProfileSerializer(serializers.ModelSerializer):
    """Safe user profile serializer — public-facing, no sensitive data."""

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "role",
            "is_verified",
            "profile_picture",
            "date_joined",
        ]
        read_only_fields = ["id", "username", "role", "is_verified", "date_joined"]

    def validate_profile_picture(self, value):
        if value and value.size > 15 * 1024 * 1024:
            raise serializers.ValidationError("Profile picture must be under 15MB.")
        return value
