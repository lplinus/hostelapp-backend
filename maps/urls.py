from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropertyPinpointViewSet

app_name = "maps"

router = DefaultRouter()
router.register("pinpoints", PropertyPinpointViewSet, basename="pinpoint")

urlpatterns = [
    path("", include(router.urls)),
]
