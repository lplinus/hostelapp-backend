from django.contrib import admin
from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from Hbackend.base_models import SoftDeleteAdmin
from .models import GuestProfile, GuestDocument, GuestDocumentSetting


class GuestDocumentInline(admin.TabularInline):
    model = GuestDocument
    extra = 0
    fields = (
        "is_primary_guest",
        "member_name",
        "document_type",
        "file_name",
        "file",
        "verification_status",
        "created_at",
    )
    readonly_fields = ("created_at",)


@admin.register(GuestProfile)
class GuestProfileAdmin(SoftDeleteAdmin):
    inlines = [GuestDocumentInline]
    list_display = (
        "full_name",
        "username_display",
        "phone_number",
        "email",
        "effective_document_limit",
        "id_verification_status_badge",
        "aadhaar_document_preview",
        "created_at",
    )
    list_filter = ("id_verification_status", "gender", "created_at")
    search_fields = (
        "full_name",
        "user__username",
        "user__email",
        "email",
        "phone_number",
        "aadhaar_number",
        "city",
        "state",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "aadhaar_document_preview",
    )

    fieldsets = (
        (
            "Guest Identity & User Link",
            {
                "fields": (
                    "user",
                    "full_name",
                    "email",
                    "phone_number",
                    "date_of_birth",
                    "gender",
                    "nationality",
                    "max_document_uploads",
                )
            },
        ),
        (
            "Address Details",
            {
                "fields": (
                    "address_line",
                    "city",
                    "state",
                    "pincode",
                )
            },
        ),
        (
            "Aadhaar & Verification Details (Fast Check-in)",
            {
                "fields": (
                    "aadhaar_number",
                    "aadhaar_card_file",
                    "aadhaar_original_name",
                    "aadhaar_document_preview",
                    "id_verification_status",
                    "share_id_with_host",
                    "verified_at",
                    "rejection_reason",
                )
            },
        ),
        (
            "Emergency Contact Information",
            {
                "fields": (
                    "emergency_contact_name",
                    "emergency_contact_phone",
                    "emergency_contact_relation",
                )
            },
        ),
        (
            "Audit Timestamps",
            {
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def username_display(self, obj):
        return obj.user.username if obj.user else "—"
    username_display.short_description = "Account Username"

    def effective_document_limit(self, obj):
        if obj.max_document_uploads is not None:
            return format_html(
                '<span style="padding: 2px 7px; border-radius: 4px; font-weight: 600; font-size: 11px; background: #ede9fe; color: #5b21b6;">{} (Custom Override)</span>',
                obj.max_document_uploads
            )
        limit = obj.effective_max_document_uploads
        return format_html(
            '<span style="padding: 2px 7px; border-radius: 4px; font-weight: 600; font-size: 11px; background: #f1f5f9; color: #334155;">{} (Global Admin Setting)</span>',
            limit
        )
    effective_document_limit.short_description = "Document Limit"

    def id_verification_status_badge(self, obj):
        color_map = {
            GuestProfile.VerificationStatus.VERIFIED: "background-color: #d1fae5; color: #065f46; border: 1px solid #a7f3d0;",
            GuestProfile.VerificationStatus.PENDING: "background-color: #fef3c7; color: #92400e; border: 1px solid #fde68a;",
            GuestProfile.VerificationStatus.REJECTED: "background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca;",
            GuestProfile.VerificationStatus.UNVERIFIED: "background-color: #f3f4f6; color: #374151; border: 1px solid #e5e7eb;",
        }
        style = color_map.get(obj.id_verification_status, "background-color: #f3f4f6; color: #374151;")
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; {}">{}</span>',
            style,
            obj.get_id_verification_status_display(),
        )
    id_verification_status_badge.short_description = "KYC Status"

    def aadhaar_document_preview(self, obj):
        if obj.aadhaar_card_file:
            return format_html(
                '<a href="{}" target="_blank" style="color: #4f46e5; font-weight: 600; text-decoration: underline;">View Uploaded Document ({})</a>',
                obj.aadhaar_card_file.url,
                obj.aadhaar_original_name or "Aadhaar Card",
            )
        return mark_safe('<span style="color: #9ca3af; font-size: 12px;">No document uploaded</span>')
    aadhaar_document_preview.short_description = "Aadhaar Document"


@admin.register(GuestDocument)
class GuestDocumentAdmin(SoftDeleteAdmin):
    list_display = (
        "member_name",
        "role_badge",
        "document_type_badge",
        "file_name",
        "guest_username",
        "booking_reference",
        "verification_status",
        "created_at",
    )
    list_filter = ("is_primary_guest", "document_type", "verification_status", "created_at")
    search_fields = (
        "member_name",
        "file_name",
        "document_number",
        "booking_reference",
        "guest_profile__user__username",
        "guest_profile__full_name",
    )

    def role_badge(self, obj):
        if obj.is_primary_guest:
            return mark_safe('<span style="padding: 2px 6px; border-radius: 4px; background-color: #e0e7ff; color: #3730a3; font-weight: 600; font-size: 11px;">Primary Guest</span>')
        return mark_safe('<span style="padding: 2px 6px; border-radius: 4px; background-color: #f3f4f6; color: #4b5563; font-weight: 600; font-size: 11px;">Member / Friend</span>')
    role_badge.short_description = "Role"

    def document_type_badge(self, obj):
        return format_html('<span style="padding: 2px 6px; border-radius: 4px; background-color: #fef3c7; color: #92400e; font-weight: 500; font-size: 11px;">{}</span>', obj.get_document_type_display())
    document_type_badge.short_description = "Category"

    def guest_username(self, obj):
        return obj.guest_profile.user.username if obj.guest_profile and obj.guest_profile.user else "—"
    guest_username.short_description = "Guest Account"


@admin.register(GuestDocumentSetting)
class GuestDocumentSettingAdmin(admin.ModelAdmin):
    list_display = ("__str__", "max_document_uploads", "updated_at")
    list_editable = ("max_document_uploads",)

    fieldsets = (
        (
            "📋 Global Document Upload Settings",
            {
                "fields": ("max_document_uploads",),
                "description": (
                    "Set the maximum identity documents a guest can upload across primary guest and companion members. "
                    "When saved here (e.g. changed to 3), the frontend and backend validation instantly reflect this limit."
                ),
            },
        ),
    )

    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False

