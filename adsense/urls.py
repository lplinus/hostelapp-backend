from django.urls import path
from .views import (
    OwnerCampaignListCreateView,
    OwnerCampaignDetailView,
    OwnerCampaignBulkDeleteView,
    OwnerPropertiesForAdView,
    PublicActiveSponsoredAdsView,
    TrackAdImpressionView,
    TrackAdClickView,
    AdPlansListView,
)

app_name = "adsense"

urlpatterns = [
    # Plans & Pricing
    path("plans/", AdPlansListView.as_view(), name="ad_plans"),

    # Owner In-House Campaign Management
    path("campaigns/", OwnerCampaignListCreateView.as_view(), name="campaigns_list_create"),
    path("campaigns/bulk-delete/", OwnerCampaignBulkDeleteView.as_view(), name="campaigns_bulk_delete"),
    path("campaigns/<int:pk>/", OwnerCampaignDetailView.as_view(), name="campaign_detail"),
    path("my-properties/", OwnerPropertiesForAdView.as_view(), name="my_properties_for_ad"),

    # Public Serving & Real-Time Tracking
    path("active-sponsored/", PublicActiveSponsoredAdsView.as_view(), name="public_active_sponsored"),
    path("track-impression/", TrackAdImpressionView.as_view(), name="track_impression"),
    path("track-click/", TrackAdClickView.as_view(), name="track_click"),
]
