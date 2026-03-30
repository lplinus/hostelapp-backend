from rest_framework import serializers
from accounts.models import User
from vendors.serializers import VendorSerializer


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

    password = serializers.CharField(write_only=True, required=False, min_length=8)
    vendor_profile = VendorSerializer(read_only=True)

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
            "is_email_verified",
            "is_phone_verified",
            "profile_picture",
            "date_joined",
            "password",
            "vendor_profile",
        ]
        read_only_fields = [
            "id",
            "username",
            "role",
            "is_verified",
            "is_email_verified",
            "is_phone_verified",
            "date_joined",
            "vendor_profile",
        ]

    def validate_profile_picture(self, value):
        if value and value.size > 15 * 1024 * 1024:
            raise serializers.ValidationError("Profile picture must be under 15MB.")
        return value

    def update(self, instance, validated_data):
        # Handle password update
        password = validated_data.pop("password", None)
        if password and password != "********":
            instance.set_password(password)

        # Reset phone verification if the phone number is changed via profile edit
        new_phone = validated_data.get("phone")
        if new_phone is not None and new_phone != instance.phone:
            instance.is_phone_verified = False
        return super().update(instance, validated_data)
