from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CountryViewSet,
    StateViewSet,
    CityViewSet,
    AreaViewSet,
    CityHostelsAPIView,
    SearchHostelsAPIView,
    InnerSearchHostelsAPIView,
    ForwardGeocodeAPIView,
)

router = DefaultRouter()
router.register("countries", CountryViewSet, basename="country")
router.register("states", StateViewSet, basename="state")
router.register("cities", CityViewSet, basename="city")
router.register("areas", AreaViewSet, basename="area")

urlpatterns = [
    path("geocode/", ForwardGeocodeAPIView.as_view(), name="forward-geocode"),
    path("search/", SearchHostelsAPIView.as_view(), name="search-hostels"),
    path(
        "inner-search/",
        InnerSearchHostelsAPIView.as_view(),
        name="inner-search-hostels",
    ),
    path(
        "cities/<slug:slug>/hostels/", CityHostelsAPIView.as_view(), name="city-hostels"
    ),
    path("", include(router.urls)),
]
