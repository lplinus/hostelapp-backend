import re
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from .models import (
    VacationRental,
    VacationRentalImage,
    VacationRentalAvailability,
    VacationRentalBooking,
    VacationRentalGuest,
    VacationRentalPayment,
    VacationRentalCancellation,
)
from locations.models import City, Area
from amenities.models import Amenity


# ── Nested & Supporting Serializers ──────────────────────────────────────────

class VacationRentalImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationRentalImage
        fields = ("id", "image", "caption", "is_primary", "order", "created_at")


class VacationRentalAvailabilitySerializer(serializers.ModelSerializer):
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)

    class Meta:
        model = VacationRentalAvailability
        fields = ("id", "rental", "date", "is_available", "custom_price", "reason", "reason_display")


class VacationRentalGuestSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationRentalGuest
        fields = (
            "guest_name",
            "guest_email",
            "mobile_number",
            "adults",
            "children",
            "infants",
            "pets",
            "total_guests",
            "special_requests",
            "created_at",
        )
        read_only_fields = ("total_guests", "created_at")


class VacationRentalPaymentSerializer(serializers.ModelSerializer):
    payment_status_display = serializers.CharField(source="get_payment_status_display", read_only=True)
    payment_method_display = serializers.CharField(source="get_payment_method_display", read_only=True)

    class Meta:
        model = VacationRentalPayment
        fields = (
            "nightly_rate_applied",
            "stay_subtotal",
            "cleaning_fee",
            "service_fee",
            "security_deposit",
            "discount_amount",
            "total_price",
            "payment_method",
            "payment_method_display",
            "payment_status",
            "payment_status_display",
            "transaction_id",
            "paid_at",
            "created_at",
        )
        read_only_fields = ("created_at",)


class VacationRentalCancellationSerializer(serializers.ModelSerializer):
    cancelled_by_display = serializers.CharField(source="get_cancelled_by_display", read_only=True)
    refund_status_display = serializers.CharField(source="get_refund_status_display", read_only=True)

    class Meta:
        model = VacationRentalCancellation
        fields = (
            "cancellation_policy_applied",
            "cancelled_by",
            "cancelled_by_display",
            "reason",
            "refund_amount",
            "refund_status",
            "refund_status_display",
            "cancelled_at",
        )
        read_only_fields = ("cancelled_at",)


# ── Vacation Rental Read & Write Serializers ─────────────────────────────────

class VacationRentalSerializer(serializers.ModelSerializer):
    """Full read serializer for Airbnb-style vacation rental detail & catalog."""
    rental_type_display = serializers.CharField(source="get_rental_type_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    cancellation_policy_display = serializers.CharField(source="get_cancellation_policy_display", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    area_name = serializers.CharField(source="area.name", read_only=True, allow_null=True)
    host_name = serializers.CharField(source="host.get_full_name", read_only=True)
    images = VacationRentalImageSerializer(many=True, read_only=True)
    amenities_list = serializers.SerializerMethodField()

    class Meta:
        model = VacationRental
        fields = (
            "id",
            "host",
            "host_name",
            "title",
            "slug",
            "tagline",
            "description",
            "short_description",
            "rental_type",
            "rental_type_display",
            "category",
            "category_display",
            "city",
            "city_name",
            "area",
            "area_name",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "max_guests",
            "bedrooms",
            "beds",
            "bathrooms",
            "price_per_night",
            "weekend_price_per_night",
            "cleaning_fee",
            "security_deposit",
            "weekly_discount_percentage",
            "monthly_discount_percentage",
            "min_nights",
            "max_nights",
            "check_in_time",
            "check_out_time",
            "instant_book",
            "cancellation_policy",
            "cancellation_policy_display",
            "allows_pets",
            "allows_smoking",
            "allows_parties",
            "custom_rules",
            "caretaker_name",
            "caretaker_number",
            "wifi_name",
            "wifi_password",
            "amenities",
            "amenities_list",
            "rating_avg",
            "rating_count",
            "is_superhost",
            "is_featured",
            "is_verified",
            "is_active",
            "og_image",
            "meta_title",
            "meta_description",
            "images",
            "created_at",
            "updated_at",
        )

    def get_amenities_list(self, obj):
        return [{"id": a.id, "name": a.name, "icon": getattr(a, "icon", None)} for a in obj.amenities.all()]


class VacationRentalWriteSerializer(serializers.ModelSerializer):
    """Write serializer for hosts adding or editing vacation rental properties."""
    class Meta:
        model = VacationRental
        fields = (
            "id",
            "title",
            "slug",
            "tagline",
            "description",
            "short_description",
            "rental_type",
            "category",
            "city",
            "area",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "max_guests",
            "bedrooms",
            "beds",
            "bathrooms",
            "price_per_night",
            "weekend_price_per_night",
            "cleaning_fee",
            "security_deposit",
            "weekly_discount_percentage",
            "monthly_discount_percentage",
            "min_nights",
            "max_nights",
            "check_in_time",
            "check_out_time",
            "instant_book",
            "cancellation_policy",
            "allows_pets",
            "allows_smoking",
            "allows_parties",
            "custom_rules",
            "caretaker_name",
            "caretaker_number",
            "wifi_name",
            "wifi_password",
            "amenities",
            "og_image",
            "meta_title",
            "meta_description",
            "is_active",
        )
        read_only_fields = ("id", "slug")


# ── Vacation Rental Booking Serializers ──────────────────────────────────────

class VacationRentalBookingSerializer(serializers.ModelSerializer):
    """Read serializer for complete booking record with decomposed details."""
    rental_title = serializers.CharField(source="rental.title", read_only=True)
    host_name = serializers.CharField(source="host.username", read_only=True)
    owner_name = serializers.CharField(source="owner.username", read_only=True)
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    guest_details = VacationRentalGuestSerializer(read_only=True)
    pricing_details = VacationRentalPaymentSerializer(read_only=True)
    cancellation_details = VacationRentalCancellationSerializer(read_only=True)

    # Flattened read-only fields for unified dashboard compatibility
    guest_name = serializers.CharField(source="guest_details.guest_name", read_only=True)
    guest_email = serializers.CharField(source="guest_details.guest_email", read_only=True)
    mobile_number = serializers.CharField(source="guest_details.mobile_number", read_only=True)
    payment_method = serializers.CharField(source="pricing_details.payment_method", read_only=True)
    payment_status = serializers.CharField(source="pricing_details.payment_status", read_only=True)

    class Meta:
        model = VacationRentalBooking
        fields = (
            "id",
            "booking_reference",
            "user",
            "rental",
            "rental_title",
            "host",
            "host_name",
            "owner",
            "owner_name",
            "owner_email",
            "check_in_date",
            "check_out_date",
            "number_of_nights",
            "total_price",
            "status",
            "status_display",
            "guest_name",
            "guest_email",
            "mobile_number",
            "payment_method",
            "payment_status",
            "guest_details",
            "pricing_details",
            "cancellation_details",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "booking_reference", "number_of_nights", "created_at", "updated_at")


class VacationRentalBookingCreateSerializer(serializers.Serializer):
    """Write serializer validating Airbnb reservation input, pricing, and availability."""
    rental_id = serializers.UUIDField()
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()

    # Guest headcount
    guest_name = serializers.CharField(max_length=255)
    guest_email = serializers.EmailField()
    mobile_number = serializers.CharField(max_length=20)
    adults = serializers.IntegerField(default=1, min_value=1)
    children = serializers.IntegerField(default=0, min_value=0)
    infants = serializers.IntegerField(default=0, min_value=0)
    pets = serializers.IntegerField(default=0, min_value=0)
    special_requests = serializers.CharField(required=False, allow_blank=True, default="")
    otp = serializers.CharField(required=False, allow_blank=True, max_length=10, default="")

    # Payment
    payment_method = serializers.ChoiceField(
        choices=VacationRentalPayment.PaymentMethod.choices,
        default=VacationRentalPayment.PaymentMethod.ONLINE,
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
        rental_id = data.get("rental_id")
        adults = data.get("adults", 1)
        children = data.get("children", 0)
        pets = data.get("pets", 0)

        # 1. Date sanity checks
        today = timezone.now().date()
        if check_in < today:
            raise serializers.ValidationError({"check_in_date": "Check-in date cannot be in the past."})
        if check_in >= check_out or (check_out - check_in).days < 1:
            raise serializers.ValidationError({"check_out_date": "Minimum stay is 1 day. Check-out date must be strictly after check-in date."})

        # 2. Rental property validation
        try:
            rental = VacationRental.objects.get(id=rental_id, is_active=True)
        except VacationRental.DoesNotExist:
            raise serializers.ValidationError({"rental_id": "Vacation rental does not exist or is inactive."})

        # 3. Night limits
        nights = (check_out - check_in).days
        if rental.min_nights and nights < rental.min_nights:
            raise serializers.ValidationError(
                {"check_out_date": f"Minimum stay for this property is {rental.min_nights} night(s)."}
            )
        if rental.max_nights and nights > rental.max_nights:
            raise serializers.ValidationError(
                {"check_out_date": f"Maximum stay for this property is {rental.max_nights} night(s)."}
            )

        # 4. Capacity and rules
        total_guests = adults + children
        if total_guests > rental.max_guests:
            raise serializers.ValidationError(
                {"adults": f"Total guests ({total_guests}) exceeds maximum capacity of {rental.max_guests}."}
            )
        if pets > 0 and not rental.allows_pets:
            raise serializers.ValidationError({"pets": "This property does not allow pets."})

        # 5. Overlapping booking check
        overlap_booking = (
            VacationRentalBooking.objects.filter(rental=rental)
            .filter(check_in_date__lt=check_out, check_out_date__gt=check_in)
            .exclude(status__in=[VacationRentalBooking.BookingStatus.CANCELLED, VacationRentalBooking.BookingStatus.DECLINED])
        )
        if overlap_booking.exists():
            raise serializers.ValidationError(
                {"check_in_date": "These dates are already booked. Please choose different dates."}
            )

        # 6. Blocked calendar availability check
        blocked_dates = VacationRentalAvailability.objects.filter(
            rental=rental,
            date__gte=check_in,
            date__lt=check_out,
            is_available=False,
        )
        if blocked_dates.exists():
            raise serializers.ValidationError(
                {"check_in_date": "One or more selected dates are blocked by the host."}
            )

        # 7. Duplicate guest booking check for same vacation rental and overlapping dates
        from django.db.models import Q
        guest_email = data.get("guest_email", "").strip().lower()
        mobile_number = data.get("mobile_number", "").strip()

        duplicate_query = Q()
        if mobile_number:
            duplicate_query |= Q(guest_details__mobile_number=mobile_number)
        if guest_email:
            duplicate_query |= Q(guest_details__guest_email__iexact=guest_email)

        if duplicate_query:
            existing_vr_bookings = (
                VacationRentalBooking.objects.filter(duplicate_query, rental=rental)
                .filter(check_in_date__lt=check_out, check_out_date__gt=check_in)
                .exclude(status__in=[VacationRentalBooking.BookingStatus.CANCELLED, VacationRentalBooking.BookingStatus.DECLINED])
            )
            if self.instance:
                existing_vr_bookings = existing_vr_bookings.exclude(pk=self.instance.pk)

            if existing_vr_bookings.exists():
                raise serializers.ValidationError(
                    f"A booking already exists for this guest at {rental.title} during the selected dates ({check_in} to {check_out}). "
                    "You cannot have multiple active bookings at the same property for overlapping dates."
                )

        # 8. OTP Verification Pipeline (mirroring hostel booking system)
        from datetime import timedelta
        from django.db.models import Q
        from bookings.models import BookingOTP, Booking
        from bookings.services.booking_otp_service import BookingOTPService

        guest_email = data.get("guest_email", "").strip().lower()
        mobile_number = data.get("mobile_number", "").strip()
        otp_code = str(data.get("otp") or "").strip()

        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None

        is_verified = False

        # Criterion A: Logged-in verified user
        if user and (getattr(user, "is_email_verified", False) or getattr(user, "is_phone_verified", False)):
            is_verified = True

        # Criterion B: Explicit OTP code supplied in payload
        if not is_verified and otp_code:
            v_email = BookingOTPService.verify_booking_email_otp(guest_email, otp_code)
            v_phone = BookingOTPService.verify_booking_otp(mobile_number, otp_code) if not v_email else False
            if v_email or v_phone:
                is_verified = True
            else:
                raise serializers.ValidationError({"otp": "Invalid or expired OTP verification code."})

        # Criterion C: Verified in preceding step via BookingOTP
        if not is_verified:
            recent_cutoff = timezone.now() - timedelta(minutes=30)
            has_recent_otp = BookingOTP.objects.filter(
                is_used=True,
                created_at__gte=recent_cutoff,
            ).filter(
                Q(email__iexact=guest_email) | Q(phone=mobile_number)
            ).exists()
            if has_recent_otp:
                is_verified = True

        # Criterion D: Smart verification skip (prior confirmed rental or hostel booking)
        if not is_verified:
            has_prior_rental = VacationRentalBooking.objects.filter(
                Q(guest_details__mobile_number=mobile_number) | Q(guest_details__guest_email__iexact=guest_email),
                status__in=[VacationRentalBooking.BookingStatus.CONFIRMED, VacationRentalBooking.BookingStatus.CHECKED_IN, VacationRentalBooking.BookingStatus.COMPLETED],
            ).exists()

            has_prior_hostel = Booking.objects.filter(
                Q(mobile_number=mobile_number) | Q(guest_email__iexact=guest_email),
                status__in=["confirmed", "completed"],
            ).exists()

            if has_prior_rental or has_prior_hostel:
                is_verified = True

        if not is_verified:
            raise serializers.ValidationError(
                {"verification": "OTP verification required before confirming the booking. Please verify your phone or email."}
            )

        data["rental"] = rental
        return data

    @transaction.atomic
    def create(self, validated_data):
        rental = VacationRental.objects.select_for_update().get(pk=validated_data["rental"].pk)
        check_in = validated_data["check_in_date"]
        check_out = validated_data["check_out_date"]
        adults = validated_data.get("adults", 1)
        children = validated_data.get("children", 0)
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else None
        if not user:
            guest_email = validated_data.get("guest_email")
            mobile_number = validated_data.get("mobile_number")
            from accounts.models import User
            if guest_email:
                user = User.objects.filter(email__iexact=guest_email).first()
            if not user and mobile_number:
                user = User.objects.filter(phone=mobile_number).first()

        # Re-verify availability after locking (prevents race condition between
        # two simultaneous requests that both passed the serializer validate())
        overlap_booking = (
            VacationRentalBooking.objects.filter(rental=rental)
            .filter(check_in_date__lt=check_out, check_out_date__gt=check_in)
            .exclude(status__in=[
                VacationRentalBooking.BookingStatus.CANCELLED,
                VacationRentalBooking.BookingStatus.DECLINED,
            ])
        )
        if overlap_booking.exists():
            raise serializers.ValidationError(
                {"check_in_date": "This property is no longer available for the selected dates. Please try again."}
            )

        blocked_dates = VacationRentalAvailability.objects.filter(
            rental=rental,
            date__gte=check_in,
            date__lt=check_out,
            is_available=False,
        )
        if blocked_dates.exists():
            raise serializers.ValidationError(
                {"check_in_date": "One or more selected dates have been blocked. Please try again."}
            )

        # ── Pricing Engine ───────────────────────────────────────────────────
        nights = (check_out - check_in).days
        base_rate = Decimal(str(rental.price_per_night))
        weekend_rate = Decimal(str(rental.weekend_price_per_night)) if rental.weekend_price_per_night else base_rate

        # Tally nightly rates day-by-day (accounting for custom rates & weekend surges)
        stay_subtotal = Decimal("0.00")
        current_date = check_in
        while current_date < check_out:
            custom_rec = VacationRentalAvailability.objects.filter(rental=rental, date=current_date).first()
            if custom_rec and custom_rec.custom_price:
                stay_subtotal += Decimal(str(custom_rec.custom_price))
            elif current_date.weekday() in (4, 5):  # Friday or Saturday
                stay_subtotal += weekend_rate
            else:
                stay_subtotal += base_rate
            current_date += timedelta(days=1)

        # Apply discounts
        discount_amount = Decimal("0.00")
        if nights >= 28 and rental.monthly_discount_percentage:
            discount_amount = (stay_subtotal * rental.monthly_discount_percentage) / Decimal("100")
        elif nights >= 7 and rental.weekly_discount_percentage:
            discount_amount = (stay_subtotal * rental.weekly_discount_percentage) / Decimal("100")

        discounted_subtotal = max(Decimal("0.00"), stay_subtotal - discount_amount)
        cleaning_fee = Decimal(str(rental.cleaning_fee or 0))
        security_deposit = Decimal(str(rental.security_deposit or 0))
        service_fee = (discounted_subtotal * Decimal("0.05")).quantize(Decimal("0.01"))  # 5% platform fee

        total_price = discounted_subtotal + cleaning_fee + service_fee

        # ── Approval Status ──────────────────────────────────────────────────
        initial_status = (
            VacationRentalBooking.BookingStatus.CONFIRMED
            if rental.instant_book
            else VacationRentalBooking.BookingStatus.PENDING_APPROVAL
        )

        # 1. Create Core Booking
        owner = rental.host
        booking = VacationRentalBooking.objects.create(
            user=user,
            rental=rental,
            host=owner,
            owner=owner,
            check_in_date=check_in,
            check_out_date=check_out,
            number_of_nights=nights,
            total_price=total_price,
            status=initial_status,
        )

        # 2. Create Modular Guest Record
        VacationRentalGuest.objects.create(
            booking=booking,
            guest_name=validated_data["guest_name"],
            guest_email=validated_data["guest_email"],
            mobile_number=validated_data["mobile_number"],
            adults=adults,
            children=children,
            infants=validated_data.get("infants", 0),
            pets=validated_data.get("pets", 0),
            total_guests=adults + children,
            special_requests=validated_data.get("special_requests", ""),
        )

        # 3. Create Modular Payment Record
        avg_nightly_rate = (stay_subtotal / Decimal(str(nights))).quantize(Decimal("0.01"))
        VacationRentalPayment.objects.create(
            booking=booking,
            nightly_rate_applied=avg_nightly_rate,
            stay_subtotal=stay_subtotal,
            cleaning_fee=cleaning_fee,
            service_fee=service_fee,
            security_deposit=security_deposit,
            discount_amount=discount_amount,
            total_price=total_price,
            payment_method=validated_data.get("payment_method", VacationRentalPayment.PaymentMethod.ONLINE),
            payment_status=VacationRentalPayment.PaymentStatus.PENDING,
        )

        # 4. If instant booking confirmed, block dates in availability calendar
        if initial_status == VacationRentalBooking.BookingStatus.CONFIRMED:
            current_date = check_in
            while current_date < check_out:
                VacationRentalAvailability.objects.update_or_create(
                    rental=rental,
                    date=current_date,
                    defaults={"is_available": False, "reason": VacationRentalAvailability.BlockReason.BOOKED},
                )
                current_date += timedelta(days=1)

        return booking
