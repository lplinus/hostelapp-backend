from rest_framework import serializers
from .models import Booking, HostelInquiry


class BookingSerializer(serializers.ModelSerializer):
    hostel_name = serializers.ReadOnlyField(source="hostel.name")
    room_category = serializers.SerializerMethodField()
    payment_id = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = "__all__"
        read_only_fields = ("user", "payment_status")

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

    # booking data validation===========================
    def validate(self, data):
        check_in = data.get("check_in")
        check_out = data.get("check_out")
        mobile_number = data.get("mobile_number")
        guest_email = data.get("guest_email")
        hostel = data.get("hostel")

        if not check_in or not check_out:
            return data

        from django.db.models import Q

        # Check for overlapping bookings with the same mobile or email
        # ONLY for the SAME hostel (as per user requirement)
        duplicate_query = Q()
        if mobile_number:
            duplicate_query |= Q(mobile_number=mobile_number)
        if guest_email:
            duplicate_query |= Q(guest_email=guest_email)

        if duplicate_query and hostel:
            existing_bookings = Booking.objects.filter(
                duplicate_query,
                hostel=hostel
            ).filter(
                check_in__lt=check_out,
                check_out__gt=check_in
            ).exclude(status="cancelled")

            if self.instance:
                existing_bookings = existing_bookings.exclude(pk=self.instance.pk)

            if existing_bookings.exists():
                raise serializers.ValidationError(
                    f"A booking already exists for this guest at {hostel.name} during the selected dates. "
                    "You cannot have multiple active bookings at the same hostel for overlapping dates."
                )

        return data

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
        return obj.payment_status


class HostelInquirySerializer(serializers.ModelSerializer):
    hostel_name = serializers.ReadOnlyField(source="hostel.name")

    class Meta:
        model = HostelInquiry
        fields = "__all__"
        read_only_fields = ("user",)
