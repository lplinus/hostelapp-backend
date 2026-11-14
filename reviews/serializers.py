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

    class Meta:
        model = Review
        fields = [
            "id",
            "booking",
            "hostel",
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

    class Meta:
        model = HotelReview
        fields = [
            "id",
            "booking",
            "hotel",
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

    class Meta:
        model = VacationRentalReview
        fields = [
            "id",
            "booking",
            "rental",
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
