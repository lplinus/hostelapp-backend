from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import AdCampaign, AdPlan
from hotels.models import Hotel
from vacanationrentals.models import VacationRental


class AdCampaignSerializer(serializers.ModelSerializer):
    ad_type_display = serializers.CharField(source="get_ad_type_display", read_only=True)
    placement_display = serializers.CharField(source="get_placement_display", read_only=True)
    property_type_display = serializers.CharField(source="get_property_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    target_property_title = serializers.ReadOnlyField()
    target_property_city = serializers.ReadOnlyField()
    target_property_price = serializers.ReadOnlyField()
    target_property_rating = serializers.ReadOnlyField()
    target_property_slug = serializers.ReadOnlyField()
    target_property_address = serializers.ReadOnlyField()
    property_image_url = serializers.SerializerMethodField()
    banner_image_url = serializers.SerializerMethodField()
    ctr = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    is_active_serving = serializers.ReadOnlyField()

    class Meta:
        model = AdCampaign
        fields = [
            "id",
            "campaign_name",
            "ad_type",
            "ad_type_display",
            "placement",
            "placement_display",
            "property_type",
            "property_type_display",
            "hotel",
            "vacation_rental",
            "hostel",
            "target_property_title",
            "target_property_city",
            "target_property_address",
            "target_property_slug",
            "target_property_price",
            "target_property_rating",
            "property_image_url",
            "banner_image",
            "banner_image_url",
            "destination_url",
            "duration_days",
            "budget",
            "start_date",
            "end_date",
            "status",
            "status_display",
            "impressions_count",
            "clicks_count",
            "ctr",
            "days_remaining",
            "is_active_serving",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "impressions_count",
            "clicks_count",
            "created_at",
            "updated_at",
        ]

    def get_property_image_url(self, obj):
        request = self.context.get("request")
        if obj.vacation_rental:
            img = obj.vacation_rental.images.filter(is_deleted=0).order_by("order").first()
            if img and img.image:
                return request.build_absolute_uri(img.image.url) if request else str(img.image)
        elif obj.hotel:
            img = obj.hotel.images.filter(is_deleted=0).order_by("order").first()
            if img and img.image:
                return request.build_absolute_uri(img.image.url) if request else str(img.image)
        elif obj.hostel:
            img = obj.hostel.images.filter(is_deleted=0).order_by("order").first()
            if img and img.image:
                return request.build_absolute_uri(img.image.url) if request else str(img.image)
        return None

    def get_banner_image_url(self, obj):
        if not obj.banner_image:
            return None
        request = self.context.get("request")
        try:
            return obj.banner_image.url
        except Exception:
            return request.build_absolute_uri(obj.banner_image.url) if request else str(obj.banner_image)


class AdCampaignCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdCampaign
        fields = [
            "campaign_name",
            "ad_type",
            "placement",
            "property_type",
            "hotel",
            "vacation_rental",
            "hostel",
            "banner_image",
            "destination_url",
            "duration_days",
            "budget",
            "start_date",
        ]

    def validate(self, attrs):
        prop_type = attrs.get("property_type")
        hotel = attrs.get("hotel")
        vacation_rental = attrs.get("vacation_rental")
        hostel = attrs.get("hostel")

        if prop_type == AdCampaign.PropertyType.HOTEL and not hotel:
            raise serializers.ValidationError({"hotel": "Please select a Hotel for this campaign."})
        elif prop_type == AdCampaign.PropertyType.VACATION_RENTAL and not vacation_rental:
            raise serializers.ValidationError({"vacation_rental": "Please select a Vacation Rental for this campaign."})
        elif prop_type == AdCampaign.PropertyType.HOSTEL and not hostel:
            raise serializers.ValidationError({"hostel": "Please select a Hostel for this campaign."})

        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        duration = validated_data.get("duration_days", 15)
        start_date = validated_data.get("start_date") or timezone.now()
        end_date = start_date + timedelta(days=duration)

        campaign = AdCampaign.objects.create(
            owner=user,
            end_date=end_date,
            status=AdCampaign.CampaignStatus.ACTIVE,
            **validated_data
        )
        return campaign


class OwnerPropertyOptionSerializer(serializers.Serializer):
    """Returns hotels and vacation rentals owned by the current logged-in owner."""
    id = serializers.CharField()
    title = serializers.CharField()
    property_type = serializers.CharField()
    city_name = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    rating = serializers.FloatField()
    image_url = serializers.CharField(allow_null=True)


class AdPlanSerializer(serializers.ModelSerializer):
    duration_display = serializers.ReadOnlyField()

    class Meta:
        model = AdPlan
        fields = [
            "id",
            "plan_code",
            "name",
            "duration_days",
            "duration_display",
            "price",
            "description",
            "is_popular",
            "is_active",
            "order",
        ]
