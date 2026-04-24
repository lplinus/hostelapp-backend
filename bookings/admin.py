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
        "id",
        "user",
        "hostel",
        "room_type",
        "check_in",
        "check_out",
        "status",
    )
    list_filter = ("status", "check_in", "check_out")
    search_fields = ("user__email", "guest_email", "hostel__name")


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
