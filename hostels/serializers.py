from rest_framework import serializers
from .models import Hostel, HostelImage, DefaultHostelImage, HostelTypeImage, Landmark, ExtraCharge
from amenities.serializers import AmenitySerializer


class LandmarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Landmark
        fields = ["id", "name", "distance", "is_popular"]


class ExtraChargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraCharge
        fields = ["id", "charge_type", "amount", "description"]


from amenities.models import Amenity
from locations.serializers import CitySerializer, AreaSerializer
from reviews.serializers import ReviewSerializer
from rooms.serializers import RoomTypeSerializer


import bleach


def validate_image_file(image):
    if not image:
        return image
    ext = image.name.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        raise serializers.ValidationError(
            "Only JPG, JPEG, PNG, and WebP files are allowed."
        )
    if image.size > 30 * 1024 * 1024:
        raise serializers.ValidationError("File size must be under 30MB.")
    return image


class HostelImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelImage
        fields = [
            "id",
            "hostel",
            "image",
            "image2",
            "image3",
            "image4",
            "image5",
            "image6",
            "image7",
            "image8",
            "image9",
            "image10",
            "alt_text",
            "is_primary",
            "order",
            "provider",
        ]

    def validate_image(self, value):
        return validate_image_file(value)

    def validate_image2(self, value):
        return validate_image_file(value)

    def validate_image3(self, value):
        return validate_image_file(value)

    def validate_image4(self, value):
        return validate_image_file(value)

    def validate_image5(self, value):
        return validate_image_file(value)

    def validate_image6(self, value):
        return validate_image_file(value)

    def validate_image7(self, value):
        return validate_image_file(value)

    def validate_image8(self, value):
        return validate_image_file(value)

    def validate_image9(self, value):
        return validate_image_file(value)

    def validate_image10(self, value):
        return validate_image_file(value)


class DefaultHostelImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultHostelImage
        fields = [
            "id",
            "image1",
            "image2",
            "image3",
            "image4",
            "image5",
            "image6",
            "image7",
            "image8",
            "image9",
            "image10",
            "alt_text",
        ]


class HostelTypeImageSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = HostelTypeImage
        fields = ["id", "hostel_type", "name", "image", "alt_text"]

    def get_name(self, obj):
        # Returns the human-readable label for the choices (e.g., "Boys Hostel")
        choices = dict(Hostel.HostelType.choices)
        return choices.get(obj.hostel_type, obj.hostel_type)


class HostelSerializer(serializers.ModelSerializer):
    images = HostelImageSerializer(many=True, read_only=True)
    amenities = AmenitySerializer(many=True, read_only=True)
    city = CitySerializer(read_only=True)
    area = AreaSerializer(read_only=True)
    room_types = RoomTypeSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    landmarks = LandmarkSerializer(many=True, read_only=True)
    extra_charges = ExtraChargeSerializer(many=True, read_only=True)
    default_images = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = Hostel
        fields = [
            "id",
            "name",
            "hostel_type",
            "suitable_for",
            "room_types",
            "slug",
            "meta_title",
            "meta_description",
            "meta_keywords",
            "canonical_url",
            "og_image",
            "og_title",
            "og_description",
            "og_type",
            "structured_data",
            "is_indexed",
            "owner",
            "city",
            "area",
            "description",
            "short_description",
            "price",
            "price_per_day",
            "is_discounted",
            "discount_percentage",
            "discounted_price",
            "discounted_price_per_day",
            "final_price",
            "final_price_per_day",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "check_in_time",
            "check_out_time",
            "rating_avg",
            "hostel_rating_avg",
            "food_rating_avg",
            "room_rating_avg",
            "rating_count",
            "is_active",
            "is_featured",
            "is_approved",
            "is_verified",
            "is_toprated",
            "amenities",
            "images",
            "default_images",
            "reviews",
            "landmarks",
            "extra_charges",
            "created_at",
        ]

    def get_rating_count(self, obj):
        return obj.reviews.filter(is_approved=True).count()

    def get_reviews(self, obj):
        # Only return approved reviews
        reviews = (
            obj.reviews.filter(is_approved=True)
            .select_related("user")
            .order_by("-created_at")
        )
        return ReviewSerializer(reviews, many=True, context=self.context).data

    def get_final_price(self, obj):
        return obj.final_price

    def get_final_price_per_day(self, obj):
        return obj.final_price_per_day

    def get_default_images(self, obj):
        """Return default images only when the hostel has no images."""
        if obj.images.exists():
            return None
        try:
            defaults = DefaultHostelImage.objects.get(pk=1)
            return DefaultHostelImageSerializer(defaults, context=self.context).data
        except DefaultHostelImage.DoesNotExist:
            return None


class HostelWriteSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating hostels (accepts city/area as IDs)."""

    amenities = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Amenity.objects.all(),
        required=False,
    )
    extra_charges = ExtraChargeSerializer(many=True, required=False)

    class Meta:
        model = Hostel
        fields = [
            "id",
            "name",
            "hostel_type",
            "suitable_for",
            "slug",
            "city",
            "area",
            "description",
            "short_description",
            "price",
            "price_per_day",
            "is_discounted",
            "discount_percentage",
            "address",
            "postal_code",
            "latitude",
            "longitude",
            "check_in_time",
            "check_out_time",
            "is_active",
            "amenities",
            "extra_charges",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        amenities = validated_data.pop("amenities", [])
        extra_charges_data = validated_data.pop("extra_charges", [])
        hostel = super().create(validated_data)
        if amenities:
            hostel.amenities.set(amenities)
        for charge_data in extra_charges_data:
            from .models import ExtraCharge
            ExtraCharge.objects.create(hostel=hostel, **charge_data)
        return hostel

    def update(self, instance, validated_data):
        amenities = validated_data.pop("amenities", None)
        extra_charges_data = validated_data.pop("extra_charges", None)
        instance = super().update(instance, validated_data)

        if amenities is not None:
            instance.amenities.set(amenities)

        if extra_charges_data is not None:
            from .models import ExtraCharge
            instance.extra_charges.all().delete()
            for charge_data in extra_charges_data:
                ExtraCharge.objects.create(hostel=instance, **charge_data)
        return instance

    def validate_short_description(self, value):
        if value:
            return bleach.clean(value, strip=True)
        return value

    def validate_description(self, value):
        if value:
            allowed_tags = getattr(
                bleach.sanitizer, "ALLOWED_TAGS", bleach.ALLOWED_TAGS
            )
            allowed_attrs = getattr(
                bleach.sanitizer, "ALLOWED_ATTRIBUTES", bleach.ALLOWED_ATTRIBUTES
            )
            return bleach.clean(
                value, tags=allowed_tags, attributes=allowed_attrs, strip=True
            )
        return value


class CityHostelListSerializer(serializers.ModelSerializer):
    area_name = serializers.CharField(source="area.name", read_only=True)
    city_name = serializers.CharField(source="city.name", read_only=True)
    thumbnail = serializers.SerializerMethodField()
    final_price = serializers.SerializerMethodField()
    rating = serializers.FloatField(source="rating_avg", read_only=True)
    rating_count = serializers.SerializerMethodField()
    room_types = RoomTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Hostel
        fields = [
            "id",
            "name",
            "slug",
            "hostel_type",
            "suitable_for",
            "price",
            "price_per_day",
            "is_discounted",
            "discount_percentage",
            "final_price",
            "final_price_per_day",
            "rating",
            "rating_count",
            "thumbnail",
            "area_name",
            "city_name",
            "is_verified",
            "is_approved",
            "room_types",
        ]

    def get_rating_count(self, obj):
        return obj.reviews.filter(is_approved=True).count()

    def get_final_price(self, obj):
        return obj.final_price

    def get_thumbnail(self, obj):
        # 1. Try to find a primary or first image from the hostel's own images
        image_obj = obj.images.filter(is_primary=True).first() or obj.images.first()
        if image_obj:
            # Check all 10 possible image fields in the HostelImage instance
            for i in range(1, 11):
                field_name = "image" if i == 1 else f"image{i}"
                img_field = getattr(image_obj, field_name, None)
                if img_field and hasattr(img_field, "url"):
                    request = self.context.get("request")
                    return (
                        request.build_absolute_uri(img_field.url)
                        if request
                        else img_field.url
                    )

        # 2. Fallback to singleton DefaultHostelImage (all 10 fields)
        try:
            defaults = DefaultHostelImage.objects.get(pk=1)
            for i in range(1, 11):
                field_name = f"image{i}"
                img_field = getattr(defaults, field_name, None)
                if img_field and hasattr(img_field, "url"):
                    request = self.context.get("request")
                    return (
                        request.build_absolute_uri(img_field.url)
                        if request
                        else img_field.url
                    )
        except DefaultHostelImage.DoesNotExist:
            pass
        return None
