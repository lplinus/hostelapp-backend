from rest_framework import serializers
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    hostel_name = serializers.ReadOnlyField(source="hostel.name")
    room_category = serializers.SerializerMethodField()
    payment_id = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = "__all__"
        read_only_fields = ("user",)

    def validate_guest_name(self, value):
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Name must be at least 3 characters long."
            )
        return value

    def validate_mobile_number(self, value):
        import re

        if not re.match(r"^\+?[\d\s-]{10,}$", value):
            raise serializers.ValidationError(
                "Enter a valid mobile number (at least 10 digits)."
            )
        return value

    def validate_guest_age(self, value):
        if value < 10 or value > 100:
            raise serializers.ValidationError("Age must be between 10 and 100.")
        return value

    def get_room_category(self, obj):
        if hasattr(obj, "room_type") and obj.room_type:
            return f"{obj.room_type.get_room_category_display()} - {obj.room_type.get_sharing_type_display()}"
        return None

    def get_payment_id(self, obj):
        if hasattr(obj, "payment"):
            return obj.payment.razorpay_payment_id or obj.payment.transaction_id
        return None

    def get_payment_status(self, obj):
        if hasattr(obj, "payment"):
            return obj.payment.status
        return None
