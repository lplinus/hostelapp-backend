from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoomTypeViewSet, BedViewSet

router = DefaultRouter()
router.register("room-types", RoomTypeViewSet, basename="room-type")
router.register("beds", BedViewSet, basename="bed")

urlpatterns = [
    path("", include(router.urls)),
]
