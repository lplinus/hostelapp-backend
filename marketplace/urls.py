from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductViewSet

from .search import MarketplaceSearchAPIView

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    path("search/", MarketplaceSearchAPIView.as_view(), name="marketplace_search"),
    path("", include(router.urls)),
]