from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    HostelViewSet,
    HostelImageViewSet,
    HostelTypeImageViewSet,
    TypeHostelsAPIView,
)

router = DefaultRouter()
router.register("hostels", HostelViewSet, basename="hostel")
router.register("images", HostelImageViewSet, basename="hostel-image")
router.register("types", HostelTypeImageViewSet, basename="hostel-type-image")

urlpatterns = [
    path("types/<str:type_slug>/hostels/",TypeHostelsAPIView.as_view(),name="type-hostels",),
    path("", include(router.urls)),
]
