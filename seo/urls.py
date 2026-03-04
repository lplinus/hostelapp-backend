from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SeoMetaViewSet

router = DefaultRouter()
router.register("", SeoMetaViewSet, basename="seo-meta")

urlpatterns = [
    path("", include(router.urls)),
]
