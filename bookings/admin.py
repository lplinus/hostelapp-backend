from django.contrib import admin

# Register your models here.
# from .models import Booking

# admin.site.register(Booking)


from django.contrib import admin
from .models import Booking, BookingEmailLog, BookingOTP, HostelInquiry
from Hbackend.base_models import SoftDeleteAdmin




@admin.register(Booking)
class BookingAdmin(SoftDeleteAdmin):
    list_display = (
        "short_id",
        "guest_name",
        "mobile_number",
        "guest_email",
        "hostel",
        "room_type",
        "check_in",
        "check_out",
        "total_price",
        "payment_method",
        "payment_status",
        "status",
        "created_at",
    )
    list_filter = (
        "status",
        "payment_status",
        "payment_method",
        "booking_type",
        "check_in",
        "check_out",
        "created_at",
    )
    search_fields = (
        "id",
        "guest_name",
        "guest_email",
        "mobile_number",
        "user__username",
        "user__email",
        "user__phone",
        "hostel__name",
    )
    readonly_fields = ("id", "created_at")

    fieldsets = (
        (
            "Guest Information",
            {
                "fields": (
                    "guest_name",
                    "mobile_number",
                    "guest_email",
                    "guest_age",
                    "user",
                )
            },
        ),
        (
            "Hostel & Room Details",
            {
                "fields": (
                    "hostel",
                    "room_type",
                    "adults",
                    "children",
                    "guests_count",
                )
            },
        ),
        (
            "Stay & Schedule",
            {
                "fields": (
                    "check_in",
                    "check_out",
                    "booking_type",
                    "stay_duration",
                    "cooldown_until",
                )
            },
        ),
        (
            "Payment & Booking Status",
            {
                "fields": (
                    "total_price",
                    "payment_method",
                    "payment_status",
                    "status",
                )
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "id",
                    "created_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def short_id(self, obj):
        return f"STN-{str(obj.id)[:8].upper()}"

    short_id.short_description = "Booking ID"


@admin.register(BookingEmailLog)
class BookingEmailLogAdmin(admin.ModelAdmin):
    list_display = (
        "booking_id",
        "email",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("booking_id", "email")
    readonly_fields = ("created_at",)


@admin.register(BookingOTP)
class BookingOTPAdmin(admin.ModelAdmin):
    list_display = (
        "phone",
        "code",
        "expires_at",
        "is_used",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("phone", "code")
    readonly_fields = ("created_at",)


@admin.register(HostelInquiry)
class HostelInquiryAdmin(admin.ModelAdmin):
    list_display = (
        "guest_name",
        "mobile_number",
        "hostel",
        "user",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("guest_name", "mobile_number", "hostel__name")
    readonly_fields = ("created_at",)
