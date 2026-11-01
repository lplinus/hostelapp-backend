from django.contrib import admin
from Hbackend.base_models import SoftDeleteAdmin
from .models import (
    VacationRental,
    VacationRentalImage,
    VacationRentalAvailability,
    VacationRentalBooking,
    VacationRentalGuest,
    VacationRentalPayment,
    VacationRentalCancellation,
)


class VacationRentalImageInline(admin.TabularInline):
    model = VacationRentalImage
    extra = 1
    fields = ("image", "caption", "is_primary", "order")


class VacationRentalAvailabilityInline(admin.TabularInline):
    model = VacationRentalAvailability
    extra = 1
    fields = ("date", "is_available", "custom_price", "reason")


class VacationRentalGuestInline(admin.StackedInline):
    model = VacationRentalGuest
    can_delete = False
    extra = 0
    fields = ("guest_name", "guest_email", "mobile_number", "adults", "children", "infants", "pets", "total_guests", "special_requests")
    readonly_fields = ("total_guests",)


class VacationRentalPaymentInline(admin.StackedInline):
    model = VacationRentalPayment
    can_delete = False
    extra = 0
    fields = (
        "nightly_rate_applied",
        "stay_subtotal",
        "cleaning_fee",
        "service_fee",
        "security_deposit",
        "discount_amount",
        "total_price",
        "payment_method",
        "payment_status",
        "transaction_id",
        "paid_at",
    )


class VacationRentalCancellationInline(admin.StackedInline):
    model = VacationRentalCancellation
    can_delete = False
    extra = 0
    fields = ("cancellation_policy_applied", "cancelled_by", "reason", "refund_amount", "refund_status", "cancelled_at")
    readonly_fields = ("cancelled_at",)


@admin.register(VacationRental)
class VacationRentalAdmin(SoftDeleteAdmin):
    list_display = (
        "title",
        "category",
        "rental_type",
        "city",
        "host",
        "price_per_night",
        "max_guests",
        "bedrooms",
        "rating_avg",
        "instant_book",
        "is_superhost",
        "is_featured",
        "is_active",
        "is_approved",
    )
    list_filter = (
        "category",
        "rental_type",
        "city",
        "instant_book",
        "is_superhost",
        "is_featured",
        "is_active",
        "is_approved",
    )
    search_fields = ("title", "host__username", "host__email", "city__name", "area__name", "address")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [VacationRentalImageInline, VacationRentalAvailabilityInline]
    filter_horizontal = ("amenities",)


@admin.register(VacationRentalImage)
class VacationRentalImageAdmin(SoftDeleteAdmin):
    list_display = ("rental", "caption", "is_primary", "order", "created_at")
    list_filter = ("is_primary", "rental")


@admin.register(VacationRentalAvailability)
class VacationRentalAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("rental", "date", "is_available", "custom_price", "reason")
    list_filter = ("is_available", "reason", "rental")
    search_fields = ("rental__title", "date")


@admin.register(VacationRentalBooking)
class VacationRentalBookingAdmin(SoftDeleteAdmin):
    list_display = (
        "booking_reference",
        "rental",
        "host",
        "check_in_date",
        "check_out_date",
        "number_of_nights",
        "total_price",
        "status",
        "created_at",
    )
    list_filter = ("status", "rental", "check_in_date")
    search_fields = (
        "booking_reference",
        "rental__title",
        "host__username",
        "guest_details__guest_name",
        "guest_details__mobile_number",
    )
    readonly_fields = ("booking_reference", "number_of_nights", "created_at", "updated_at")
    inlines = [VacationRentalGuestInline, VacationRentalPaymentInline, VacationRentalCancellationInline]


@admin.register(VacationRentalGuest)
class VacationRentalGuestAdmin(SoftDeleteAdmin):
    list_display = ("booking", "guest_name", "guest_email", "mobile_number", "total_guests", "adults", "children")
    search_fields = ("guest_name", "guest_email", "mobile_number", "booking__booking_reference")


@admin.register(VacationRentalPayment)
class VacationRentalPaymentAdmin(SoftDeleteAdmin):
    list_display = ("booking", "total_price", "payment_method", "payment_status", "transaction_id", "paid_at")
    list_filter = ("payment_status", "payment_method")
    search_fields = ("booking__booking_reference", "transaction_id")


@admin.register(VacationRentalCancellation)
class VacationRentalCancellationAdmin(SoftDeleteAdmin):
    list_display = ("booking", "cancellation_policy_applied", "cancelled_by", "refund_amount", "refund_status", "cancelled_at")
    list_filter = ("cancelled_by", "refund_status")
    search_fields = ("booking__booking_reference", "reason")
