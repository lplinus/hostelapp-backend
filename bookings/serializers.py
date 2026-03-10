from rest_framework import serializers
from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    hostel_name = serializers.ReadOnlyField(source="hostel.name")
    room_category = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = "__all__"
        read_only_fields = ("user",)

    def get_room_category(self, obj):
        if hasattr(obj, "room_type") and obj.room_type:
            return f"{obj.room_type.get_room_category_display()} - {obj.room_type.get_sharing_type_display()}"
        return None
