from rest_framework import serializers
from .models import Review, HotelReview, VacationRentalReview


def _extract_user_display_name(obj):
    if obj.name:
        return obj.name
    if obj.user:
        first = obj.user.first_name or ""
        last = obj.user.last_name or ""
        full = f"{first} {last}".strip()
        return full if full else obj.user.username
    return "Anonymous"


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    hostel_name = serializers.CharField(source="hostel.name", read_only=True, default="")
    hostel_slug = serializers.CharField(source="hostel.slug", read_only=True, default="")
    booking_reference = serializers.CharField(source="booking.booking_reference", read_only=True, default="")

    class Meta:
        model = Review
        fields = [
            "id",
            "booking",
            "hostel",
            "hostel_name",
            "hostel_slug",
            "booking_reference",
            "user",
            "name",
            "rating",
            "hostel_rating",
            "food_rating",
            "room_rating",
            "comment",
            "user_name",
            "created_at",
        ]
        read_only_fields = ("user", "rating")

    def get_user_name(self, obj):
        return _extract_user_display_name(obj)


class HotelReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    hotel_name = serializers.CharField(source="hotel.name", read_only=True, default="")
    hotel_slug = serializers.CharField(source="hotel.slug", read_only=True, default="")
    booking_reference = serializers.CharField(source="booking.booking_reference", read_only=True, default="")

    class Meta:
        model = HotelReview
        fields = [
            "id",
            "booking",
            "hotel",
            "hotel_name",
            "hotel_slug",
            "booking_reference",
            "user",
            "name",
            "rating",
            "cleanliness_rating",
            "comfort_rating",
            "service_rating",
            "location_rating",
            "comment",
            "user_name",
            "created_at",
        ]
        read_only_fields = ("user", "rating")

    def get_user_name(self, obj):
        return _extract_user_display_name(obj)


class VacationRentalReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    rental_title = serializers.CharField(source="rental.title", read_only=True, default="")
    rental_slug = serializers.CharField(source="rental.slug", read_only=True, default="")
    booking_reference = serializers.CharField(source="booking.booking_reference", read_only=True, default="")

    class Meta:
        model = VacationRentalReview
        fields = [
            "id",
            "booking",
            "rental",
            "rental_title",
            "rental_slug",
            "booking_reference",
            "user",
            "name",
            "rating",
            "cleanliness_rating",
            "accuracy_rating",
            "checkin_rating",
            "communication_rating",
            "location_rating",
            "value_rating",
            "comment",
            "user_name",
            "created_at",
        ]
        read_only_fields = ("user", "rating")

    def get_user_name(self, obj):
        return _extract_user_display_name(obj)
