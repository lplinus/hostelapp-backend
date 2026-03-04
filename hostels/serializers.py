from rest_framework import serializers
from .models import Hostel, HostelImage, DefaultHostelImage, HostelTypeImage
from amenities.serializers import AmenitySerializer
from locations.serializers import CitySerializer, AreaSerializer
from reviews.serializers import ReviewSerializer
from rooms.serializers import RoomTypeSerializer


class HostelImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelImage
        fields = [
            "id",
            "image",
            "image2",
            "image3",
            "image4",
            "alt_text",
            "is_primary",
            "order",
        ]


class DefaultHostelImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultHostelImage
        fields = ["id", "image1", "image2", "image3", "image4", "alt_text"]


class HostelTypeImageSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = HostelTypeImage
        fields = ["id", "hostel_type", "name", "image", "alt_text"]

    def get_name(self, obj):
        # Returns the human-readable label for the choices (e.g., "Boys Hostel")
        choices = dict(Hostel.HostelType.choices)
        return choices.get(obj.hostel_type, obj.hostel_type)


# class HostelSerializer(serializers.ModelSerializer):
#     images = HostelImageSerializer(many=True, read_only=True)
#     amenities = AmenitySerializer(many=True, read_only=True)
#     city = CitySerializer(read_only=True)
#     area = AreaSerializer(read_only=True)
#     room_types = RoomTypeSerializer(many=True, read_only=True)
#     reviews = ReviewSerializer(many=True, read_only=True)
#     default_images = serializers.SerializerMethodField()

#     class Meta:
#         model = Hostel
#         fields = [
#             "id",
#             "name",
#             "hostel_type",
#             "room_types",
#             "slug",
#             "owner",
#             "city",
#             "area",
#             "description",
#             "short_description",
#             "price",
#             "address",
#             "postal_code",
#             "latitude",
#             "longitude",
#             "check_in_time",
#             "check_out_time",
#             "rating_avg",
#             "rating_count",
#             "is_active",
#             "is_featured",
#             "is_verified",
#             "is_toprated",
#             "amenities",
#             "images",
#             "default_images",
#             "reviews",
#             "created_at",
#         ]




class HostelSerializer(serializers.ModelSerializer):
    images = HostelImageSerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    city = CitySerializer(read_only=True)
    area = AreaSerializer(read_only=True)
    room_types = RoomTypeSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    default_images = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()

    class Meta:
        model = Hostel
        fields = [
            "id",
            "name",
            "hostel_type",
            "room_types",
            "slug",
            "owner",
            "city",
            "area",
            "description",
            "short_description",
            "price",
            "is_discounted",
            "discount_percentage",
            "discounted_price",
            "final_price",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "check_in_time",
            "check_out_time",
            "rating_avg",
            "rating_count",
            "is_active",
            "is_featured",
            "is_verified",
            "is_toprated",
            "amenities",
            "images",
            "default_images",
            "reviews",
            "created_at",
        ]

    def get_final_price(self, obj):
        return obj.final_price

    def get_default_images(self, obj):
        """Return default images only when the hostel has no images."""
        if obj.images.exists():
            return None
        try:
            defaults = DefaultHostelImage.objects.get(pk=1)
            return DefaultHostelImageSerializer(defaults, context=self.context).data
        except DefaultHostelImage.DoesNotExist:
            return None


# class CityHostelListSerializer(serializers.ModelSerializer):
#     area_name = serializers.CharField(source="area.name", read_only=True)
#     city_name = serializers.CharField(source="city.name", read_only=True)
#     thumbnail = serializers.SerializerMethodField()
    
#     base_price = serializers.DecimalField(
#         source="price", max_digits=10, decimal_places=2, read_only=True
#     )
#     rating = serializers.FloatField(source="rating_avg", read_only=True)

#     class Meta:
#         model = Hostel
#         fields = [
#             "id",
#             "name",
#             "slug",
#             "hostel_type",
#             "base_price",
#             "rating",
#             "thumbnail",
#             "area_name",
#             "city_name",
#             "is_verified",
#         ]


class CityHostelListSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source="area.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    thumbnail = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()
    rating = serializers.FloatField(source="rating_avg", read_only=True)

    class Meta:
        model = Hostel
        fields = [
            "id",
            "name",
            "slug",
            "hostel_type",
            "price",
            "is_discounted",
            "discount_percentage",
            "final_price",
            "rating",
            "thumbnail",
            "area_name",
            "city_name",
            "is_verified",
        ]

    def get_final_price(self, obj):
        return obj.final_price

    def get_thumbnail(self, obj):
        image = obj.images.filter(is_primary=True).first() or obj.images.first()
        if image and image.image:
            request = self.context.get("request")
            return (
                request.build_absolute_uri(image.image.url)
                if request
                else image.image.url
            )
        try:
            defaults = DefaultHostelImage.objects.get(pk=1)
            if defaults.image1:
                request = self.context.get("request")
                return (
                    request.build_absolute_uri(defaults.image1.url)
                    if request
                    else defaults.image1.url
                )
        except DefaultHostelImage.DoesNotExist:
            pass
        return None
