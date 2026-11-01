from django.contrib import admin
from Hbackend.base_models import SoftDeleteAdmin
from .models import (
    Hotel,
    HotelRoomType,
    HotelImage,
    HotelBooking,
    HotelGuest,
    HotelPayment,
    HotelCancellation,
)


class HotelImageInline(admin.TabularInline):
    model = HotelImage
    extra = 1
    fields = ("image", "room_type", "alt_text", "is_primary", "order")


class HotelRoomTypeInline(admin.StackedInline):
    model = HotelRoomType
    extra = 1
    fields = (
        "name",
        "room_category",
        "bed_type",
        "base_price_per_night",
        "total_rooms",
        "rooms_available",
        "max_occupancy",
        "includes_breakfast",
        "is_available",
    )


class HotelGuestInline(admin.StackedInline):
    model = HotelGuest
    can_delete = False
    extra = 0
    fields = ("guest_name", "guest_email", "mobile_number", "adults_count", "children_count", "special_requests")


class HotelPaymentInline(admin.StackedInline):
    model = HotelPayment
    can_delete = False
    extra = 0
    fields = (
        "room_rate_per_night",
        "base_amount",
        "tax_amount",
        "discount_amount",
        "total_amount",
        "payment_method",
        "payment_status",
        "transaction_id",
        "paid_at",
    )


class HotelCancellationInline(admin.StackedInline):
    model = HotelCancellation
    can_delete = False
    extra = 0
    fields = ("cancelled_by", "reason", "refund_amount", "refund_status", "cancelled_at")
    readonly_fields = ("cancelled_at",)


@admin.register(Hotel)
class HotelAdmin(SoftDeleteAdmin):
    list_display = (
        "name",
        "hotel_type",
        "star_rating",
        "city",
        "starting_price_per_night",
        "rating_avg",
        "is_featured",
        "is_active",
        "is_approved",
    )
    list_filter = ("hotel_type", "star_rating", "city", "is_featured", "is_active", "is_approved")
    search_fields = ("name", "city__name", "area__name", "address")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [HotelRoomTypeInline, HotelImageInline]
    filter_horizontal = ("amenities",)


@admin.register(HotelRoomType)
class HotelRoomTypeAdmin(SoftDeleteAdmin):
    list_display = (
        "name",
        "hotel",
        "room_category",
        "bed_type",
        "base_price_per_night",
        "total_rooms",
        "rooms_available",
        "is_available",
    )
    list_filter = ("room_category", "bed_type", "is_available", "hotel__city")
    search_fields = ("name", "hotel__name")


@admin.register(HotelImage)
class HotelImageAdmin(SoftDeleteAdmin):
    list_display = ("hotel", "room_type", "is_primary", "order", "created_at")
    list_filter = ("is_primary", "hotel")


@admin.register(HotelBooking)
class HotelBookingAdmin(SoftDeleteAdmin):
    list_display = (
        "booking_reference",
        "hotel",
        "room_type",
        "check_in_date",
        "check_out_date",
        "number_of_rooms",
        "total_amount",
        "status",
        "created_at",
    )
    list_filter = ("status", "hotel", "check_in_date")
    search_fields = ("booking_reference", "hotel__name", "guest_details__guest_name", "guest_details__mobile_number")
    readonly_fields = ("booking_reference", "number_of_nights", "created_at", "updated_at")
    inlines = [HotelGuestInline, HotelPaymentInline, HotelCancellationInline]


@admin.register(HotelGuest)
class HotelGuestAdmin(SoftDeleteAdmin):
    list_display = ("booking", "guest_name", "guest_email", "mobile_number", "adults_count", "children_count")
    search_fields = ("guest_name", "guest_email", "mobile_number", "booking__booking_reference")


@admin.register(HotelPayment)
class HotelPaymentAdmin(SoftDeleteAdmin):
    list_display = ("booking", "total_amount", "payment_method", "payment_status", "transaction_id", "paid_at")
    list_filter = ("payment_status", "payment_method")
    search_fields = ("booking__booking_reference", "transaction_id")


@admin.register(HotelCancellation)
class HotelCancellationAdmin(SoftDeleteAdmin):
    list_display = ("booking", "cancelled_by", "refund_amount", "refund_status", "cancelled_at")
    list_filter = ("cancelled_by", "refund_status")
    search_fields = ("booking__booking_reference", "reason")
