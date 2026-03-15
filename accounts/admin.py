from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, VerificationCode


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