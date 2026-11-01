from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HotelViewSet,
    HotelRoomTypeViewSet,
    HotelImageViewSet,
    HotelBookingViewSet,
)

app_name = "hotels"

router = DefaultRouter()
router.register("properties", HotelViewSet, basename="hotel")
router.register("room-types", HotelRoomTypeViewSet, basename="hotel-room-type")
router.register("images", HotelImageViewSet, basename="hotel-image")
router.register("bookings", HotelBookingViewSet, basename="hotel-booking")

# Allow direct root mappings like /api/hotels/
hotel_list = HotelViewSet.as_view({"get": "list", "post": "create"})
hotel_detail = HotelViewSet.as_view({"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"})

urlpatterns = [
    path("", include(router.urls)),
    path("", hotel_list, name="hotel-root-list"),
    path("<slug:slug>/", hotel_detail, name="hotel-root-detail"),
]
