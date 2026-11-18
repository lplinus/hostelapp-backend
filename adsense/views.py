from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db.models import F, Sum, Q
from django.shortcuts import get_object_or_404

from .models import AdCampaign, AdPlan
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
    Supports dynamic filtering by property_type (hotel, vacation_rental), placement, location/city, and limit.
    Enables interchangeability between top banner carousels and sponsored listing cards.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        now = timezone.now()
        queryset = AdCampaign.objects.filter(
            is_deleted=0,
            status=AdCampaign.CampaignStatus.ACTIVE,
            start_date__lte=now,
            end_date__gte=now,
        ).select_related("hotel", "vacation_rental", "hotel__city", "vacation_rental__city", "hostel")

        # 1. Filter by property type (hotel, vacation_rental, hostel)
        prop_type = request.query_params.get("property_type")
        if prop_type and prop_type.lower() != "all":
            queryset = queryset.filter(property_type=prop_type.lower())

        # 2. Filter by placement if specified (or all if omitted/all)
        placement = request.query_params.get("placement")
        if placement and placement.lower() != "all":
            queryset = queryset.filter(placement=placement)

        # 3. Location / City filtering (Crucial for location-based dynamic ads)
        city = request.query_params.get("city") or request.query_params.get("location") or request.query_params.get("search")
        city_id = request.query_params.get("city_id")
        city_slug = request.query_params.get("city_slug")

        if city_id:
            queryset = queryset.filter(
                Q(hotel__city_id=city_id) | Q(vacation_rental__city_id=city_id)
            )
        elif city_slug:
            queryset = queryset.filter(
                Q(hotel__city__slug=city_slug) | Q(vacation_rental__city__slug=city_slug)
            )
        elif city and city.strip():
            c = city.strip()
            queryset = queryset.filter(
                Q(hotel__city__name__icontains=c)
                | Q(vacation_rental__city__name__icontains=c)
                | Q(hotel__address__icontains=c)
                | Q(vacation_rental__address__icontains=c)
                | Q(hotel__area__name__icontains=c)
                | Q(vacation_rental__area__name__icontains=c)
            )

        try:
            limit = min(int(request.query_params.get("limit", 16)), 30)
        except (ValueError, TypeError):
            limit = 16

        serializer = AdCampaignSerializer(queryset[:limit], many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class TrackAdImpressionView(APIView):
    """
    POST: Real-time atomic increment of ad impression count.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        campaign_id = request.data.get("campaign_id")
        if not campaign_id:
            return Response({"error": "campaign_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        updated = AdCampaign.objects.filter(id=campaign_id, is_deleted=0).update(
            impressions_count=F("impressions_count") + 1
        )
        return Response({"success": bool(updated)}, status=status.HTTP_200_OK)


class TrackAdClickView(APIView):
    """
    POST: Real-time atomic increment of ad click count.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        campaign_id = request.data.get("campaign_id")
        if not campaign_id:
            return Response({"error": "campaign_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        updated = AdCampaign.objects.filter(id=campaign_id, is_deleted=0).update(
            clicks_count=F("clicks_count") + 1
        )
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

