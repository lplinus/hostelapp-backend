import os
from rest_framework import serializers
from .models import GuestProfile, GuestDocument


class GuestDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    document_type_name = serializers.CharField(source="get_document_type_display", read_only=True)

    class Meta:
        model = GuestDocument
        fields = [
            "id",
            "is_primary_guest",
            "member_name",
            "document_type",
            "document_type_name",
            "document_number",
            "file",
            "file_url",
            "file_name",
            "file_size",
            "booking_reference",
            "verification_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "file_url",
            "document_type_name",
            "file_size",
            "verification_status",
            "created_at",
            "updated_at",
        ]

    def get_file_url(self, obj):
        if obj.file:
            try:
                url = obj.file.url
                if url.startswith("http://") or url.startswith("https://"):
                    return url
                request = self.context.get("request")
                if request:
                    return request.build_absolute_uri(url)
                return url
            except Exception:
                return None
        return None


class GuestProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    profile_picture = serializers.ImageField(source="user.profile_picture", read_only=True)
    is_email_verified = serializers.BooleanField(source="user.is_email_verified", read_only=True)
    is_phone_verified = serializers.BooleanField(source="user.is_phone_verified", read_only=True)
    aadhaar_file_name = serializers.SerializerMethodField()
    aadhaar_file_url = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()
    max_document_uploads = serializers.IntegerField(source="effective_max_document_uploads", read_only=True)

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
            "max_document_uploads",
            "aadhaar_number",
            "aadhaar_card_file",
            "aadhaar_file_name",
            "aadhaar_file_url",
            "id_verification_status",
            "share_id_with_host",
            "verified_at",
            "rejection_reason",
            "is_email_verified",
            "is_phone_verified",
            "documents",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "username",
            "profile_picture",
            "max_document_uploads",
            "id_verification_status",
            "verified_at",
            "rejection_reason",
            "documents",
            "created_at",
            "updated_at",
        ]

    def get_aadhaar_file_name(self, obj):
        if obj.aadhaar_original_name:
            return obj.aadhaar_original_name
        if obj.aadhaar_card_file:
            return os.path.basename(obj.aadhaar_card_file.name)
        return None

    def get_aadhaar_file_url(self, obj):
        if obj.aadhaar_card_file:
            try:
                url = obj.aadhaar_card_file.url
                if url.startswith("http://") or url.startswith("https://"):
                    return url
                request = self.context.get("request")
                if request:
                    return request.build_absolute_uri(url)
                return url
            except Exception:
                return None
        return None

    def get_documents(self, obj):
        docs = list(obj.documents.filter(is_deleted=0))
        # Backward compatibility: if no documents in GuestDocument table yet,
        # but legacy aadhaar_card_file exists on profile, synthesize primary document
        if not any(d.is_primary_guest for d in docs) and obj.aadhaar_card_file:
            legacy_doc = {
                "id": str(obj.id),
                "is_primary_guest": True,
                "member_name": obj.full_name or "Primary Guest",
                "document_type": "aadhaar",
                "document_type_name": "Aadhaar Card",
                "document_number": obj.aadhaar_number or "",
                "file": obj.aadhaar_card_file.name if obj.aadhaar_card_file else "",
                "file_url": self.get_aadhaar_file_url(obj),
                "file_name": obj.aadhaar_original_name or (os.path.basename(obj.aadhaar_card_file.name) if obj.aadhaar_card_file else "Aadhaar_Document.pdf"),
                "file_size": 0,
                "booking_reference": "",
                "verification_status": obj.id_verification_status,
                "created_at": obj.created_at.isoformat() if obj.created_at else None,
                "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
            }
            return [legacy_doc] + [GuestDocumentSerializer(d, context=self.context).data for d in docs]
        return GuestDocumentSerializer(docs, many=True, context=self.context).data

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

        if "max_document_uploads" in validated_data:
            instance.max_document_uploads = validated_data["max_document_uploads"]

        # When a new Aadhaar document is uploaded, mark it verified and ready for self-authorized check-in
        if "aadhaar_card_file" in validated_data:
            new_file = validated_data["aadhaar_card_file"]
            if new_file:
                if instance.aadhaar_card_file and instance.aadhaar_card_file != new_file:
                    try:
                        instance.aadhaar_card_file.delete(save=False)
                    except Exception:
                        pass
                if hasattr(new_file, "name"):
                    instance.aadhaar_original_name = new_file.name
                validated_data["id_verification_status"] = GuestProfile.VerificationStatus.VERIFIED
            else:
                if instance.aadhaar_card_file:
                    try:
                        instance.aadhaar_card_file.delete(save=False)
                    except Exception:
                        pass
                instance.aadhaar_card_file = None
                instance.aadhaar_original_name = None
                validated_data["id_verification_status"] = GuestProfile.VerificationStatus.UNVERIFIED

        return super().update(instance, validated_data)
