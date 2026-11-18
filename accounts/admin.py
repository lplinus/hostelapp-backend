from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, VerificationCode, DocumentVerification, VerificationDocument
from django.utils.html import format_html


class VerificationDocumentInline(admin.TabularInline):
    model = VerificationDocument
    extra = 0
    fields = ("title", "document_type", "document_file_link", "file_size_display", "status", "rejection_reason", "created_at")
    readonly_fields = ("document_file_link", "file_size_display", "created_at")

    def document_file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank" class="button" style="padding: 3px 8px; font-weight: bold;">View / Download</a>', obj.file.url)
        return "-"
    document_file_link.short_description = "File"

    def file_size_display(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
        return "-"
    file_size_display.short_description = "Size"


@admin.register(DocumentVerification)
class DocumentVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_display",
        "role",
        "status",
        "documents_count",
        "verified_at",
        "verified_by",
        "created_at",
    )
    list_filter = ("role", "status", "created_at")
    search_fields = ("user__username", "user__email", "user__phone", "admin_notes")
    inlines = [VerificationDocumentInline]
    actions = ["verify_all_documents", "reject_all_documents"]

    def user_display(self, obj):
        return f"{obj.user.username} ({obj.user.email or obj.user.phone or ''})"
    user_display.short_description = "User"

    def documents_count(self, obj):
        total = obj.documents.filter(is_deleted=0).count()
        verified = obj.documents.filter(is_deleted=0, status=VerificationDocument.DocumentStatus.VERIFIED).count()
        return f"{verified} / {total} Verified"
    documents_count.short_description = "Progress"

    @admin.action(description="Approve & Verify all documents for selected users")
    def verify_all_documents(self, request, queryset):
        for verification in queryset:
            verification.documents.filter(is_deleted=0).update(status=VerificationDocument.DocumentStatus.VERIFIED)
            verification.verified_by = request.user
            verification.update_status()
        self.message_user(request, f"Successfully verified documents for {queryset.count()} user(s).")

    @admin.action(description="Reject selected document verifications")
    def reject_all_documents(self, request, queryset):
        for verification in queryset:
            verification.documents.filter(is_deleted=0).update(
                status=VerificationDocument.DocumentStatus.REJECTED,
                rejection_reason="Rejected by Super Admin."
            )
            verification.verified_by = request.user
            verification.update_status()
        self.message_user(request, f"Marked {queryset.count()} document verification(s) as rejected.")


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_display",
        "role_display",
        "title",
        "document_type",
        "status",
        "file_link",
        "file_size_display",
        "created_at",
    )
    list_filter = ("status", "document_type", "created_at")
    search_fields = ("title", "verification__user__username", "verification__user__email")
    actions = ["mark_verified", "mark_rejected"]

    def user_display(self, obj):
        return obj.verification.user.username if obj.verification else "-"
    user_display.short_description = "User"

    def role_display(self, obj):
        return obj.verification.get_role_display() if obj.verification else "-"
    role_display.short_description = "Role"

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank" style="font-weight: bold; text-decoration: underline;">Open Document</a>', obj.file.url)
        return "-"
    file_link.short_description = "File"

    def file_size_display(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
        return "-"
    file_size_display.short_description = "Size"

    @admin.action(description="Mark selected documents as Verified")
    def mark_verified(self, request, queryset):
        for doc in queryset:
            doc.status = VerificationDocument.DocumentStatus.VERIFIED
            doc.rejection_reason = None
            doc.save()
            doc.verification.verified_by = request.user
            doc.verification.update_status()
        self.message_user(request, f"Marked {queryset.count()} document(s) as Verified.")

    @admin.action(description="Mark selected documents as Rejected")
    def mark_rejected(self, request, queryset):
        for doc in queryset:
            doc.status = VerificationDocument.DocumentStatus.REJECTED
            doc.rejection_reason = "Rejected by Super Admin."
            doc.save()
            doc.verification.verified_by = request.user
            doc.verification.update_status()
        self.message_user(request, f"Marked {queryset.count()} document(s) as Rejected.")



@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "id",
        "username",
        "email",
        "phone",
        "role",
        "is_email_verified",
        "is_phone_verified",
        "is_verified",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    list_filter = (
        "role",
        "is_email_verified",
        "is_phone_verified",
        "is_verified",
        "is_active",
        "is_staff",
        "is_superuser",
    )
    list_editable = (
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
    )

    search_fields = (
        "username",
        "email",
        "phone",
    )

    ordering = ("id",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Custom Fields",
            {
                "fields": (
                    "role",
                    "phone",
                    "profile_picture",
                    "is_email_verified",
                    "is_phone_verified",
                    "is_verified",
                )
            },
        ),
    )


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "code",
        "type",
        "is_used",
        "created_at",
        "expires_at",
    )

    list_filter = (
        "type",
        "is_used",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__phone",
        "code",
    )

    ordering = ("-created_at",)