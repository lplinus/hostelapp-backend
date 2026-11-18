from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from accounts.models import DocumentVerification, VerificationDocument


class VerificationDocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source="get_document_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    file_url = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    delete_cooldown_seconds_remaining = serializers.SerializerMethodField()

    class Meta:
        model = VerificationDocument
        fields = [
            "id",
            "document_type",
            "document_type_display",
            "title",
            "file",
            "file_url",
            "file_size",
            "status",
            "status_display",
            "rejection_reason",
            "can_delete",
            "delete_cooldown_seconds_remaining",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "file_size",
            "status",
            "status_display",
            "rejection_reason",
            "can_delete",
            "delete_cooldown_seconds_remaining",
            "created_at",
            "updated_at",
        ]

    def get_file_url(self, obj):
        if not obj.file:
            return None
        try:
            return obj.file.url
        except Exception:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file.url)
            return str(obj.file)

    def get_can_delete(self, obj):
        # Once verified or if verification is verified, cannot delete
        if obj.status == VerificationDocument.DocumentStatus.VERIFIED:
            return False
        if obj.verification and obj.verification.status == DocumentVerification.VerificationStatus.VERIFIED:
            return False

        # If rejected, owner can always delete to replace it
        if obj.status == VerificationDocument.DocumentStatus.REJECTED:
            return True

        # Cooldown check: 10 minutes limit (600 seconds)
        if obj.created_at:
            elapsed = (timezone.now() - obj.created_at).total_seconds()
            return elapsed <= 600
        return True

    def get_delete_cooldown_seconds_remaining(self, obj):
        if obj.status == VerificationDocument.DocumentStatus.VERIFIED:
            return 0
        if obj.status == VerificationDocument.DocumentStatus.REJECTED:
            return 0
        if obj.created_at:
            elapsed = (timezone.now() - obj.created_at).total_seconds()
            return max(0, int(600 - elapsed))
        return 0


class DocumentVerificationSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    documents = VerificationDocumentSerializer(many=True, read_only=True)
    uploaded_count = serializers.SerializerMethodField()
    remaining_slots = serializers.SerializerMethodField()

    class Meta:
        model = DocumentVerification
        fields = [
            "id",
            "role",
            "role_display",
            "status",
            "status_display",
            "admin_notes",
            "verified_at",
            "documents",
            "uploaded_count",
            "remaining_slots",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "role",
            "role_display",
            "status",
            "status_display",
            "admin_notes",
            "verified_at",
            "documents",
            "uploaded_count",
            "remaining_slots",
            "created_at",
            "updated_at",
        ]

    def get_uploaded_count(self, obj):
        return obj.documents.filter(is_deleted=0).count()

    def get_remaining_slots(self, obj):
        count = obj.documents.filter(is_deleted=0).count()
        return max(0, 5 - count)


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    document_type = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")

    def validate_file(self, value):
        if not value:
            raise serializers.ValidationError("A valid file is required.")
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size exceeds 5MB limit. Please upload a file smaller than or equal to 5MB.")
        return value
