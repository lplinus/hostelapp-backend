# from rest_framework import serializers
# from .models import RoomType, Bed


# class RoomTypeSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = RoomType
#         fields = "__all__"


# class BedSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Bed
#         fields = "__all__"




from rest_framework import serializers
from .models import RoomType, Bed


class BedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bed
        fields = [
            "id",
            "bed_number",
            "is_available",
            "total_beds",
            "beds_available",
        ]


class RoomTypeSerializer(serializers.ModelSerializer):
    beds = BedSerializer(many=True, read_only=True)

    sharing_display = serializers.CharField(
        source="get_sharing_type_display",
        read_only=True,
    )

    category_display = serializers.CharField(
        source="get_room_category_display",
        read_only=True,
    )

    available_beds = serializers.SerializerMethodField()

    class Meta:
        model = RoomType
        fields = [
            "id",
            # "name",
            # "description",
            "room_category",
            "category_display",
            "sharing_type",
            "sharing_display",
            "base_price",
            "is_available",
            "available_beds",
            "beds",
        ]

    def get_available_beds(self, obj):
        return obj.beds.filter(is_available=True).count()