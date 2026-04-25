from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, VendorNotificationViewSet

router = DefaultRouter()
router.register(r'vendor', VendorNotificationViewSet, basename='vendor-notification')
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]