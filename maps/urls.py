from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropertyPinpointViewSet, MapPlaceViewSet, get_map_properties

app_name = "maps"

router = DefaultRouter()
router.register("pinpoints", PropertyPinpointViewSet, basename="pinpoint")
router.register("places", MapPlaceViewSet, basename="map-place")

urlpatterns = [
    path("", include(router.urls)),
    path('properties/', get_map_properties, name='map-properties-api'),
]