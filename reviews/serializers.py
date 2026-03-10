from rest_framework import serializers
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = "__all__"
        read_only_fields = ("user",)

    def get_user_name(self, obj):
        if obj.user:
            first = obj.user.first_name or ""
            last = obj.user.last_name or ""
            full = f"{first} {last}".strip()
            return full if full else obj.user.username
        return "Anonymous"
