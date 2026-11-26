import random
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import F, Sum, Q
from django.shortcuts import get_object_or_404
from django.core.cache import cache

from .models import AdCampaign, AdPlan
from .services import get_active_banner_campaigns
from .serializers import (
    AdCampaignSerializer,
    AdCampaignCreateSerializer,
    OwnerPropertyOptionSerializer,
    AdPlanSerializer,
)
from hotels.models import Hotel
from vacanationrentals.models import VacationRental


class OwnerCampaignListCreateView(APIView):
    """
    GET: List all campaigns created by the logged-in owner, with overall statistics.
    POST: Create and launch a new in-house ad campaign.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = AdCampaign.objects.filter(owner=user, is_deleted=0).order_by("-created_at")
        
        status_filter = request.query_params.get("status")
        if status_filter and status_filter.lower() != "all":
            queryset = queryset.filter(status=status_filter.lower())

        serializer = AdCampaignSerializer(queryset, many=True, context={"request": request})

        # Calculate high-level performance metrics for owner
        all_campaigns = AdCampaign.objects.filter(owner=user, is_deleted=0)
        total_impressions = all_campaigns.aggregate(Sum("impressions_count"))["impressions_count__sum"] or 0
        total_clicks = all_campaigns.aggregate(Sum("clicks_count"))["clicks_count__sum"] or 0
        active_count = all_campaigns.filter(status=AdCampaign.CampaignStatus.ACTIVE).count()
        avg_ctr = round((total_clicks / total_impressions * 100), 2) if total_impressions > 0 else 0.0

        return Response({
            "campaigns": serializer.data,
            "stats": {
                "active_campaigns": active_count,
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "avg_ctr": avg_ctr,
            }
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AdCampaignCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            campaign = serializer.save()
            return Response(
                {
                    "message": "Ad campaign launched successfully!",
                    "campaign": AdCampaignSerializer(campaign, context={"request": request}).data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OwnerCampaignDetailView(APIView):
    """
    GET: Retrieve campaign details.
    PATCH: Toggle campaign status between Active and Paused.
    DELETE: Soft-delete / archive campaign.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        return get_object_or_404(AdCampaign, id=pk, owner=user, is_deleted=0)

    def get(self, request, pk):
        campaign = self.get_object(pk, request.user)
        serializer = AdCampaignSerializer(campaign, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        campaign = self.get_object(pk, request.user)
        action = request.data.get("action")  # 'toggle', 'pause', 'resume'

        if action == "pause":
            campaign.status = AdCampaign.CampaignStatus.PAUSED
        elif action == "resume":
            campaign.status = AdCampaign.CampaignStatus.ACTIVE
        else:
            # Default toggle
            campaign.status = (
                AdCampaign.CampaignStatus.PAUSED
                if campaign.status == AdCampaign.CampaignStatus.ACTIVE
                else AdCampaign.CampaignStatus.ACTIVE
            )

        campaign.save(update_fields=["status", "updated_at"])
        return Response(
            {
                "message": f"Campaign is now {campaign.get_status_display()}.",
                "campaign": AdCampaignSerializer(campaign, context={"request": request}).data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        campaign = self.get_object(pk, request.user)
        campaign.is_deleted = 1
        campaign.save(update_fields=["is_deleted", "updated_at"])
        return Response({"message": "Campaign archived successfully."}, status=status.HTTP_200_OK)


class OwnerCampaignBulkDeleteView(APIView):
    """
    POST: Soft-delete / archive multiple ad campaigns owned by the logged-in user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ids = request.data.get("ids")
        if not isinstance(ids, list) or len(ids) == 0:
            return Response(
                {"error": "Please provide a non-empty list of campaign ids."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        updated_count = AdCampaign.objects.filter(
            id__in=ids,
            owner=request.user,
            is_deleted=0,
        ).update(is_deleted=1, updated_at=timezone.now())

        return Response(
            {
                "message": f"{updated_count} campaign(s) archived successfully.",
                "deleted_count": updated_count,
            },
            status=status.HTTP_200_OK,
        )


class OwnerPropertiesForAdView(APIView):
    """
    GET: Returns a list of Hotels and Vacation Rentals owned by the logged-in owner
    to populate the property selector when creating an Ad campaign.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        properties = []

        # 1. Fetch Hotels owned by user first
        hotels = Hotel.objects.filter(owner=user, is_deleted=0).select_related("city").prefetch_related("images")
        for h in hotels:
            first_img = h.images.filter(is_deleted=0).order_by("order").first()
            img_url = request.build_absolute_uri(first_img.image.url) if (first_img and first_img.image) else None
            properties.append({
                "id": str(h.id),
                "title": h.name,
                "property_type": "hotel",
                "property_type_display": "Hotel",
                "city_name": h.city.name if h.city else "City",
                "price": float(h.starting_price_per_night or 0),
                "rating": float(h.rating_avg or 5.0),
                "image_url": img_url,
            })

        # 2. Fetch Vacation Rentals owned by user second
        rentals = VacationRental.objects.filter(host=user, is_deleted=0).select_related("city").prefetch_related("images")
        for r in rentals:
            first_img = r.images.filter(is_deleted=0).order_by("order").first()
            img_url = request.build_absolute_uri(first_img.image.url) if (first_img and first_img.image) else None
            properties.append({
                "id": str(r.id),
                "title": r.title,
                "property_type": "vacation_rental",
                "property_type_display": "Vacation Rental",
                "city_name": r.city.name if r.city else "Destination",
                "price": float(r.price_per_night or 0),
                "rating": float(r.rating_avg or 5.0),
                "image_url": img_url,
            })

        return Response(properties, status=status.HTTP_200_OK)


class PublicActiveSponsoredAdsView(APIView):
    """
    GET: Returns active sponsored ads for search results, top banners, or landing pages.
    - Fixed schedule: start_date and end_date control running window.
    - Budget stop: max_impressions and max_clicks cap automatic serving.
    - Cache: caches placement result per city/prop_type for 60 to 120 seconds (90s).
    - Weighted random: picks properties by weight so different properties appear on page loads.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        prop_type = (request.query_params.get("property_type") or "all").lower().strip()
        placement = (request.query_params.get("placement") or "all").lower().strip()
        city = (request.query_params.get("city") or request.query_params.get("location") or request.query_params.get("search") or "").strip()
        city_id = request.query_params.get("city_id")
        city_slug = request.query_params.get("city_slug")
        search_id = request.query_params.get("search_id") or request.query_params.get("banner_seed")

        try:
            limit = min(int(request.query_params.get("limit", 4)), 4)
        except (ValueError, TypeError):
            limit = 4

        campaigns = get_active_banner_campaigns(
            property_type=prop_type,
            city=city,
            city_slug=city_slug,
            city_id=city_id,
            placement=placement,
            limit=limit,
            search_id=search_id,
        )

        serializer = AdCampaignSerializer(campaigns, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class TrackAdImpressionView(APIView):
    """
    POST: Real-time atomic increment of ad impression count.
    Automatically completes promotion if max_impressions budget cap is reached.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        campaign_id = request.data.get("campaign_id")
        if not campaign_id:
            return Response({"error": "campaign_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        updated = AdCampaign.objects.filter(id=campaign_id, is_deleted=0).update(
            impressions_count=F("impressions_count") + 1
        )

        # Check budget stop
        campaign = AdCampaign.objects.filter(id=campaign_id, is_deleted=0).first()
        if campaign and campaign.max_impressions > 0 and campaign.impressions_count >= campaign.max_impressions:
            campaign.status = AdCampaign.CampaignStatus.COMPLETED
            campaign.save(update_fields=["status", "updated_at"])

        return Response({"success": bool(updated)}, status=status.HTTP_200_OK)


class TrackAdClickView(APIView):
    """
    POST: Real-time atomic increment of ad click count.
    Automatically completes promotion if max_clicks budget cap is reached.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        campaign_id = request.data.get("campaign_id")
        if not campaign_id:
            return Response({"error": "campaign_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        updated = AdCampaign.objects.filter(id=campaign_id, is_deleted=0).update(
            clicks_count=F("clicks_count") + 1
        )

        # Check budget stop
        campaign = AdCampaign.objects.filter(id=campaign_id, is_deleted=0).first()
        if campaign and campaign.max_clicks > 0 and campaign.clicks_count >= campaign.max_clicks:
            campaign.status = AdCampaign.CampaignStatus.COMPLETED
            campaign.save(update_fields=["status", "updated_at"])

        return Response({"success": bool(updated)}, status=status.HTTP_200_OK)


class AdPlansListView(APIView):
    """
    GET: Returns all active AdSense promotion packages configured in the backend.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        plans = AdPlan.objects.filter(is_active=True, is_deleted=0).order_by("order", "duration_days")
        serializer = AdPlanSerializer(plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

