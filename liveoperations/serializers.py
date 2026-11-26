from rest_framework import serializers
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


class HousekeepingTaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    property_name = serializers.SerializerMethodField()

    class Meta:
        model = HousekeepingTask
        fields = [
            "id",
            "stream",
            "hotel",
            "vacation_rental",
            "property_name",
            "unit_identifier",
            "floor",
            "status",
            "status_display",
            "priority",
            "priority_display",
            "linen_changed",
            "restocked",
            "inspected",
            "assigned_staff",
            "notes",
            "next_check_in",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_property_name(self, obj):
        if obj.hotel:
            return obj.hotel.name
        if obj.vacation_rental:
            return obj.vacation_rental.title
        return "Unknown Property"


class PropertyDateBlockSerializer(serializers.ModelSerializer):
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    property_name = serializers.SerializerMethodField()

    class Meta:
        model = PropertyDateBlock
        fields = [
            "id",
            "stream",
            "hotel",
            "vacation_rental",
            "property_name",
            "unit_identifier",
            "start_date",
            "end_date",
            "reason",
            "reason_display",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_property_name(self, obj):
        if obj.hotel:
            return obj.hotel.name
        if obj.vacation_rental:
            return obj.vacation_rental.title
        return "Unknown Property"

    def validate(self, data):
        start = data.get("start_date")
        end = data.get("end_date")
        if start and end and start >= end:
            raise serializers.ValidationError({"end_date": "End date must be strictly after start date."})
        return data


class DigitalGuestAccessSerializer(serializers.ModelSerializer):
    kyc_status_display = serializers.CharField(source="get_kyc_status_display", read_only=True)
    guest_name = serializers.SerializerMethodField()
    guest_mobile = serializers.SerializerMethodField()
    property_name = serializers.SerializerMethodField()

    class Meta:
        model = DigitalGuestAccess
        fields = [
            "id",
            "stream",
            "hotel_booking",
            "vacation_booking",
            "property_name",
            "guest_name",
            "guest_mobile",
            "access_code",
            "wifi_ssid",
            "wifi_password",
            "instructions_sent",
            "instructions_sent_at",
            "kyc_status",
            "kyc_status_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_guest_name(self, obj):
        if obj.hotel_booking and hasattr(obj.hotel_booking, "guest_details") and obj.hotel_booking.guest_details:
            return obj.hotel_booking.guest_details.guest_name
        if obj.vacation_booking and hasattr(obj.vacation_booking, "guest_details") and obj.vacation_booking.guest_details:
            return obj.vacation_booking.guest_details.guest_name
        return "Guest"

    def get_guest_mobile(self, obj):
        if obj.hotel_booking and hasattr(obj.hotel_booking, "guest_details") and obj.hotel_booking.guest_details:
            return obj.hotel_booking.guest_details.mobile_number
        if obj.vacation_booking and hasattr(obj.vacation_booking, "guest_details") and obj.vacation_booking.guest_details:
            return obj.vacation_booking.guest_details.mobile_number
        return ""

    def get_property_name(self, obj):
        if obj.hotel_booking and obj.hotel_booking.hotel:
            return obj.hotel_booking.hotel.name
        if obj.vacation_booking and obj.vacation_booking.rental:
            return obj.vacation_booking.rental.title
        return "Property"


class SecurityDepositLedgerSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    rental_title = serializers.SerializerMethodField()
    guest_name = serializers.SerializerMethodField()
    booking_reference = serializers.SerializerMethodField()

    class Meta:
        model = SecurityDepositLedger
        fields = [
            "id",
            "vacation_booking",
            "booking_reference",
            "rental_title",
            "guest_name",
            "amount",
            "status",
            "status_display",
            "deduction_amount",
            "deduction_reason",
            "released_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_rental_title(self, obj):
        if obj.vacation_booking and obj.vacation_booking.rental:
            return obj.vacation_booking.rental.title
        return ""

    def get_guest_name(self, obj):
        if obj.vacation_booking and hasattr(obj.vacation_booking, "guest_details") and obj.vacation_booking.guest_details:
            return obj.vacation_booking.guest_details.guest_name
        return "Guest"

    def get_booking_reference(self, obj):
        if obj.vacation_booking:
            return obj.vacation_booking.booking_reference
        return ""


class LiveMealPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveMealPlan
        fields = [
            "id",
            "hotel",
            "code",
            "name",
            "surcharge",
            "desc",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LiveSeasonalMultiplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveSeasonalMultiplier
        fields = [
            "id",
            "stream",
            "hotel",
            "vacation_rental",
            "name",
            "multiplier",
            "dates",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LiveMinStayRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveMinStayRule
        fields = [
            "id",
            "stream",
            "hotel",
            "vacation_rental",
            "standard_min_nights",
            "weekend_min_nights",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LivePromoCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = LivePromoCoupon
        fields = [
            "id",
            "stream",
            "hotel",
            "vacation_rental",
            "code",
            "discount",
            "min_nights",
            "active",
            "usage_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "usage_count", "created_at", "updated_at"]
