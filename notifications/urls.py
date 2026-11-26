from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, VendorNotificationViewSet, FCMDeviceViewSet

router = DefaultRouter()
router.register(r'vendor', VendorNotificationViewSet, basename='vendor-notification')
router.register(r'devices', FCMDeviceViewSet, basename='fcm-device')
router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
