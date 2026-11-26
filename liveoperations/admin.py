from django.contrib import admin
from .models import (
    HousekeepingTask,
    PropertyDateBlock,
    DigitalGuestAccess,
    SecurityDepositLedger,
    LiveMealPlan,
    LiveSeasonalMultiplier,
    LiveMinStayRule,
    LivePromoCoupon,
)


@admin.register(HousekeepingTask)
class HousekeepingTaskAdmin(admin.ModelAdmin):
    list_display = ("unit_identifier", "stream", "status", "priority", "assigned_staff", "linen_changed", "inspected", "updated_at")
    list_filter = ("stream", "status", "priority", "linen_changed", "inspected")
    search_fields = ("unit_identifier", "assigned_staff", "notes")


@admin.register(PropertyDateBlock)
class PropertyDateBlockAdmin(admin.ModelAdmin):
    list_display = ("unit_identifier", "stream", "start_date", "end_date", "reason", "updated_at")
    list_filter = ("stream", "reason")
    search_fields = ("unit_identifier", "notes")


@admin.register(DigitalGuestAccess)
class DigitalGuestAccessAdmin(admin.ModelAdmin):
    list_display = ("access_code", "stream", "kyc_status", "instructions_sent", "instructions_sent_at")
    list_filter = ("stream", "kyc_status", "instructions_sent")
    search_fields = ("access_code", "wifi_ssid")


@admin.register(SecurityDepositLedger)
class SecurityDepositLedgerAdmin(admin.ModelAdmin):
    list_display = ("vacation_booking", "amount", "status", "deduction_amount", "released_at")
    list_filter = ("status",)
    search_fields = ("vacation_booking__booking_reference", "deduction_reason")


@admin.register(LiveMealPlan)
class LiveMealPlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "surcharge", "active", "owner", "updated_at")
    list_filter = ("active",)
    search_fields = ("code", "name")


@admin.register(LiveSeasonalMultiplier)
class LiveSeasonalMultiplierAdmin(admin.ModelAdmin):
    list_display = ("name", "multiplier", "dates", "active", "owner", "updated_at")
    list_filter = ("active",)
    search_fields = ("name", "dates")


@admin.register(LiveMinStayRule)
class LiveMinStayRuleAdmin(admin.ModelAdmin):
    list_display = ("owner", "hotel", "standard_min_nights", "weekend_min_nights", "updated_at")


@admin.register(LivePromoCoupon)
class LivePromoCouponAdmin(admin.ModelAdmin):
    list_display = ("code", "discount", "min_nights", "active", "usage_count", "owner")
    list_filter = ("active",)
    search_fields = ("code",)
