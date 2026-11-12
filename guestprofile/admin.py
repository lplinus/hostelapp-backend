from django.contrib import admin
from django.utils.html import format_html
from Hbackend.base_models import SoftDeleteAdmin
from .models import GuestProfile


@admin.register(GuestProfile)
class GuestProfileAdmin(SoftDeleteAdmin):
    list_display = (
        "full_name",
        "username_display",
        "phone_number",
        "email",
        "aadhaar_number",
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
                    "aadhaar_document_preview",
                    "id_verification_status",
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
    username_display.short_description = "Username"

    def id_verification_status_badge(self, obj):
        colors = {
            "verified": "#10b981",
            "pending": "#f59e0b",
            "rejected": "#ef4444",
            "unverified": "#6b7280",
        }
        color = colors.get(obj.id_verification_status, "#6b7280")
        label = obj.get_id_verification_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: 600; font-size: 11px;">{}</span>',
            color,
            label,
        )
    id_verification_status_badge.short_description = "Aadhaar Status"

    def aadhaar_document_preview(self, obj):
        if obj.aadhaar_card_file:
            url = obj.aadhaar_card_file.url
            if url.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                return format_html(
                    '<a href="{}" target="_blank"><img src="{}" style="max-height: 50px; border-radius: 4px; border: 1px solid #ddd;" /></a>',
                    url,
                    url,
                )
            return format_html(
                '<a href="{}" target="_blank" style="padding: 4px 8px; background: #3b82f6; color: white; border-radius: 4px; text-decoration: none; font-size: 12px;">View PDF</a>',
                url,
            )
        return "No file uploaded"
    aadhaar_document_preview.short_description = "Aadhaar Proof"
