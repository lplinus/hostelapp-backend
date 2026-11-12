import os
from rest_framework import serializers
from .models import GuestProfile


class GuestProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    profile_picture = serializers.ImageField(source="user.profile_picture", read_only=True)
    is_email_verified = serializers.BooleanField(source="user.is_email_verified", read_only=True)
    is_phone_verified = serializers.BooleanField(source="user.is_phone_verified", read_only=True)
    aadhaar_file_name = serializers.SerializerMethodField()
    aadhaar_file_url = serializers.SerializerMethodField()

    class Meta:
        model = GuestProfile
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "phone_number",
            "profile_picture",
            "date_of_birth",
            "gender",
            "nationality",
            "address_line",
            "city",
            "state",
            "pincode",
            "emergency_contact_name",
            "emergency_contact_phone",
            "emergency_contact_relation",
            "aadhaar_number",
            "aadhaar_card_file",
            "aadhaar_file_name",
            "aadhaar_file_url",
            "id_verification_status",
            "verified_at",
            "rejection_reason",
            "is_email_verified",
            "is_phone_verified",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "username",
            "profile_picture",
            "id_verification_status",
            "verified_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]

    def get_aadhaar_file_name(self, obj):
        if obj.aadhaar_card_file:
            return os.path.basename(obj.aadhaar_card_file.name)
        return None

    def get_aadhaar_file_url(self, obj):
        if obj.aadhaar_card_file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.aadhaar_card_file.url)
            return obj.aadhaar_card_file.url
        return None

    def update(self, instance, validated_data):
        user = instance.user
        full_name = validated_data.get("full_name")
        phone_number = validated_data.get("phone_number")
        email = validated_data.get("email")

        # Keep User table in sync
        user_modified = False
        if full_name is not None and full_name.strip():
            parts = full_name.strip().split(" ", 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ""
            user_modified = True

        if phone_number is not None and phone_number != user.phone:
            user.phone = phone_number
            user_modified = True

        if email is not None and email != user.email:
            user.email = email
            user_modified = True

        if user_modified:
            user.save(update_fields=["first_name", "last_name", "phone", "email"])

        # When a new Aadhaar document is uploaded, set status to pending review
        if "aadhaar_card_file" in validated_data and validated_data["aadhaar_card_file"]:
            validated_data["id_verification_status"] = GuestProfile.VerificationStatus.PENDING

        return super().update(instance, validated_data)

