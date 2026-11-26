from rest_framework import serializers
from .models import PropertyPinpoint, MapPlace


class MapPlaceSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = MapPlace
        fields = [
            "id",
            "title",
            "category",
            "description",
            "latitude",
            "longitude",
            "landmark",
            "address",
            "city",
            "phone",
            "image",
            "image_url",
            "link_url",
            "content_type",
            "object_id",
            "is_active",
            "is_featured",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return ""


class PropertyPinpointSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    distance_meters = serializers.FloatField(read_only=True, required=False)

    class Meta:
        model = PropertyPinpoint
        fields = [
            "id",
            "owner",
            "owner_username",
            "property_type",
            "property_id",
            "title",
            "latitude",
            "longitude",
            "formatted_address",
            "city",
            "area",
            "postal_code",
            "landmark",
            "directions_guide",
            "is_auto_fetched",
            "gps_accuracy",
            "offline_map_data",
            "offline_tile_bounds",
            "is_verified",
            "distance_meters",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]


class AutoFetchPinpointSerializer(serializers.Serializer):
    property_type = serializers.ChoiceField(choices=PropertyPinpoint.PROPERTY_TYPES)
    property_id = serializers.IntegerField(required=False, allow_null=True)
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    accuracy = serializers.FloatField(required=False, allow_null=True)
    formatted_address = serializers.CharField(required=False, allow_blank=True)
    landmark = serializers.CharField(required=False, allow_blank=True)
    directions_guide = serializers.CharField(required=False, allow_blank=True)
    sync_property_record = serializers.BooleanField(default=True, help_text="Sync lat/lng to hostel/hotel/rental table")


class OfflineMapPackageSerializer(serializers.Serializer):
    pinpoint = PropertyPinpointSerializer()
    offline_tile_bounds = serializers.DictField()
    center = serializers.DictField()
    recommended_zoom = serializers.ListField(child=serializers.IntegerField())
    offline_download_urls = serializers.ListField(child=serializers.CharField())