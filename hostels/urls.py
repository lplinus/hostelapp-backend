from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HostelViewSet,
    HostelImageViewSet,
    HostelTypeImageViewSet,
    TypeHostelsAPIView,
    TopRatedHostelsAPIView,
    FeaturedHostelsAPIView,
)

router = DefaultRouter()
router.register("hostels", HostelViewSet, basename="hostel")
router.register("images", HostelImageViewSet, basename="hostel-image")
router.register("types", HostelTypeImageViewSet, basename="hostel-type-image")

# For root mapping to hostels ViewSet
hostel_list = HostelViewSet.as_view({'get': 'list', 'post': 'create'})
hostel_detail = HostelViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

urlpatterns = [
    path("top-rated/", TopRatedHostelsAPIView.as_view(), name="top-rated-hostels"),
    path("featured/", FeaturedHostelsAPIView.as_view(), name="featured-hostels"),
    path("types/<str:type_slug>/hostels/",TypeHostelsAPIView.as_view(),name="type-hostels",),
    path("", include(router.urls)),
    
    # Safe fallback routes for the root /api/hostels/ mapped to same ViewSet
    # Appended after router.urls so it doesn't conflict with "images/" or "types/"
    path("", hostel_list, name="hostel-root-list"),
    path("<slug:slug>/", hostel_detail, name="hostel-root-detail"),
    path("id/<int:id>/", hostel_detail, name="hostel-root-detail-id"),
]

