import re
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from rest_framework import serializers
from .models import (
    Hotel,
    HotelRoomType,
    HotelImage,
    HotelBooking,
    HotelGuest,
    HotelPayment,
    HotelCancellation,
)
from locations.models import City, Area
from amenities.models import Amenity


# ── Nested & Supporting Serializers ──────────────────────────────────────────

class HotelImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelImage
        fields = ("id", "image", "room_type", "alt_text", "is_primary", "order", "provider", "created_at")


class HotelRoomTypeSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_room_category_display", read_only=True)
    bed_display = serializers.CharField(source="get_bed_type_display", read_only=True)
    images = HotelImageSerializer(many=True, read_only=True)

    class Meta:
        model = HotelRoomType
        fields = (
            "id",
            "hotel",
            "name",
            "room_category",
            "category_display",
            "bed_type",
            "bed_display",
            "description",
            "max_adults",
            "max_children",
            "max_occupancy",
            "total_rooms",
            "rooms_available",
            "base_price_per_night",
            "tax_percentage",
            "includes_breakfast",
            "is_refundable",
            "room_size_sqft",
            "features",
            "is_available",
            "images",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class HotelGuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelGuest
        fields = (
            "guest_name",
            "guest_email",
            "mobile_number",
            "adults_count",
            "children_count",
            "special_requests",
            "created_at",
        )
        read_only_fields = ("created_at",)


class HotelPaymentSerializer(serializers.ModelSerializer):
    payment_status_display = serializers.CharField(source="get_payment_status_display", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)

    class Meta:
        model = HotelPayment
        fields = (
            "room_rate_per_night",
            "base_amount",
            "tax_amount",
            "discount_amount",
            "total_amount",
            "payment_method",
            "payment_method_display",
            "payment_status",
            "payment_status_display",
            "transaction_id",
            "paid_at",
            "created_at",
        )
        read_only_fields = ("created_at",)


class HotelCancellationSerializer(serializers.ModelSerializer):
    cancelled_by_display = serializers.CharField(source="get_cancelled_by_display", read_only=True)
    refund_status_display = serializers.CharField(source="get_refund_status_display", read_only=True)

    class Meta:
        model = HotelCancellation
        fields = (
            "cancelled_by",
            "cancelled_by_display",
            "reason",
            "refund_amount",
            "refund_status",
            "refund_status_display",
            "cancelled_at",
        )
        read_only_fields = ("cancelled_at",)


# ── Hotel Read & Write Serializers ───────────────────────────────────────────

class HotelSerializer(serializers.ModelSerializer):
    """Full read serializer for public catalog and detail pages."""
    hotel_type_display = serializers.CharField(source="get_hotel_type_display", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    area_name = serializers.CharField(source="area.name", read_only=True, allow_null=True)
    images = HotelImageSerializer(many=True, read_only=True)
    room_types = HotelRoomTypeSerializer(many=True, read_only=True)
    amenities_list = serializers.SerializerMethodField()

    class Meta:
        model = Hotel
        fields = (
            "id",
            "name",
            "slug",
            "tagline",
            "description",
            "short_description",
            "hotel_type",
            "hotel_type_display",
            "star_rating",
            "city",
            "city_name",
            "area",
            "area_name",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "check_in_time",
            "check_out_time",
            "starting_price_per_night",
            "amenities",
            "amenities_list",
            "cancellation_policy",
            "allows_pets",
            "rating_avg",
            "rating_count",
            "is_featured",
            "is_toprated",
            "is_verified",
            "is_active",
            "og_image",
            "meta_title",
            "meta_description",
            "images",
            "room_types",
            "created_at",
            "updated_at",
        )

    def get_amenities_list(self, obj):
        return [{"id": a.id, "name": a.name, "icon": getattr(a, "icon", None)} for a in obj.amenities.all()]


class HotelWriteSerializer(serializers.ModelSerializer):
    """Write serializer for adding and updating hotels."""
    class Meta:
        model = Hotel
        fields = (
            "id",
            "name",
            "slug",
            "tagline",
            "description",
            "short_description",
            "hotel_type",
            "star_rating",
            "city",
            "area",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "check_in_time",
            "check_out_time",
            "amenities",
            "cancellation_policy",
            "allows_pets",
            "og_image",
            "meta_title",
            "meta_description",
            "is_active",
        )
        read_only_fields = ("id", "slug")


# ── Hotel Booking Serializers ────────────────────────────────────────────────

class HotelBookingSerializer(serializers.ModelSerializer):
    """Read serializer for complete booking data with decomposed relations."""
    hotel_name = serializers.CharField(source="hotel.name", read_only=True)
    room_type_name = serializers.CharField(source="room_type.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    guest_details = HotelGuestSerializer(read_only=True)
    payment_details = HotelPaymentSerializer(read_only=True)
    cancellation_details = HotelCancellationSerializer(read_only=True)

    class Meta:
        model = HotelBooking
        fields = (
            "id",
            "booking_reference",
            "user",
            "hotel",
            "hotel_name",
            "room_type",
            "room_type_name",
            "check_in_date",
            "check_out_date",
            "number_of_nights",
            "number_of_rooms",
            "total_amount",
            "status",
            "status_display",
            "guest_details",
            "payment_details",
            "cancellation_details",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "booking_reference", "number_of_nights", "created_at", "updated_at")


class HotelBookingCreateSerializer(serializers.Serializer):
    """Write serializer validating booking input and atomically creating modular models."""
    hotel_id = serializers.UUIDField()
    room_type_id = serializers.IntegerField()
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    number_of_rooms = serializers.IntegerField(default=1, min_value=1)

    # Guest Info
    guest_name = serializers.CharField(max_length=255)
    guest_email = serializers.EmailField()
    mobile_number = serializers.CharField(max_length=20)
    adults_count = serializers.IntegerField(default=1, min_value=1)
    children_count = serializers.IntegerField(default=0, min_value=0)
    special_requests = serializers.CharField(required=False, allow_blank=True)

    # Payment
    payment_method = serializers.ChoiceField(
        choices=HotelPayment.PaymentMethod.choices,
        default=HotelPayment.PaymentMethod.ONLINE,
    )

    def validate_guest_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Guest name must be at least 3 characters long.")
        return value.strip()

    def validate_mobile_number(self, value):
        cleaned = re.sub(r"[\s-]", "", value)
        if not re.match(r"^\+?\d{10,15}$", cleaned):
            raise serializers.ValidationError("Enter a valid mobile number (10 to 15 digits).")
        return cleaned

    def validate(self, data):
        check_in = data.get("check_in_date")
        check_out = data.get("check_out_date")
        hotel_id = data.get("hotel_id")
        room_type_id = data.get("room_type_id")
        rooms_requested = data.get("number_of_rooms", 1)

        # 1. Date sanity checks
        today = timezone.now().date()
        if check_in < today:
            raise serializers.ValidationError({"check_in_date": "Check-in date cannot be in the past."})
        if check_in >= check_out:
            raise serializers.ValidationError({"check_out_date": "Check-out date must be strictly after check-in date."})

        # 2. Hotel & Room Type verification
        try:
            hotel = Hotel.objects.get(id=hotel_id, is_active=True)
        except Hotel.DoesNotExist:
            raise serializers.ValidationError({"hotel_id": "Hotel does not exist or is inactive."})

        try:
            room_type = HotelRoomType.objects.get(id=room_type_id, hotel=hotel, is_available=True)
        except HotelRoomType.DoesNotExist:
            raise serializers.ValidationError({"room_type_id": "Selected room type is not available for this hotel."})

        # 3. Room inventory validation
        if room_type.rooms_available < rooms_requested:
            raise serializers.ValidationError(
                {"number_of_rooms": f"Only {room_type.rooms_available} room(s) available for {room_type.name}."}
            )

        data["hotel"] = hotel
        data["room_type"] = room_type
        return data

    @transaction.atomic
    def create(self, validated_data):
        hotel = validated_data["hotel"]
        room_type = validated_data["room_type"]
        check_in = validated_data["check_in_date"]
        check_out = validated_data["check_out_date"]
        num_rooms = validated_data.get("number_of_rooms", 1)
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None

        # Calculate pricing
        nights = (check_out - check_in).days
        rate = room_type.base_price_per_night
        base_amount = Decimal(str(rate)) * Decimal(str(nights)) * Decimal(str(num_rooms))
        tax_pct = room_type.tax_percentage or Decimal("12.00")
        tax_amount = (base_amount * tax_pct) / Decimal("100")
        total_amount = base_amount + tax_amount

        # 1. Create Core Booking
        booking = HotelBooking.objects.create(
            user=user,
            hotel=hotel,
            room_type=room_type,
            check_in_date=check_in,
            check_out_date=check_out,
            number_of_nights=nights,
            number_of_rooms=num_rooms,
            total_amount=total_amount,
            status=HotelBooking.BookingStatus.CONFIRMED,
        )

        # 2. Create Modular Guest Record
        HotelGuest.objects.create(
            booking=booking,
            guest_name=validated_data["guest_name"],
            guest_email=validated_data["guest_email"],
            mobile_number=validated_data["mobile_number"],
            adults_count=validated_data.get("adults_count", 1),
            children_count=validated_data.get("children_count", 0),
            special_requests=validated_data.get("special_requests", ""),
        )

        # 3. Create Modular Payment Record
        HotelPayment.objects.create(
            booking=booking,
            room_rate_per_night=rate,
            base_amount=base_amount,
            tax_amount=tax_amount,
            total_amount=total_amount,
            payment_method=validated_data.get("payment_method", HotelPayment.PaymentMethod.ONLINE),
            payment_status=HotelPayment.PaymentStatus.PENDING,
        )

        # 4. Decrement available room inventory
        room_type.rooms_available = max(0, room_type.rooms_available - num_rooms)
        room_type.save(update_fields=["rooms_available"])

        return booking
