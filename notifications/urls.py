from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, VendorNotificationViewSet, FCMDeviceViewSet, SupportThreadViewSet

router = DefaultRouter()
router.register(r'support-chat', SupportThreadViewSet, basename='support-chat')
router.register(r'vendor', VendorNotificationViewSet, basename='vendor-notification')
router.register(r'devices', FCMDeviceViewSet, basename='fcm-device')
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
