from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AmenityViewSet

router = DefaultRouter()
router.register("", AmenityViewSet, basename="amenity")

urlpatterns = [
    path("", include(router.urls)),
]
