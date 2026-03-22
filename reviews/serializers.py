from rest_framework import serializers
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "hostel", "user", "name", "rating", "hostel_rating", "food_rating", "room_rating", "comment", "user_name", "created_at"]
        read_only_fields = ("user", "rating")

    def get_user_name(self, obj):
        if obj.name:
            return obj.name
        if obj.user:
            first = obj.user.first_name or ""
            last = obj.user.last_name or ""
            full = f"{first} {last}".strip()
            return full if full else obj.user.username
        return "Anonymous"
