from rest_framework import serializers
from .models import Notification, VendorNotification, FCMDevice

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 
            'related_object_id', 'is_read', 'created_at'
        ]
        read_only_fields = fields

class VendorNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorNotification
        fields = [
            'id', 'title', 'message', 'notification_type', 
            'related_object_id', 'is_read', 'created_at'
        ]
        read_only_fields = fields

class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        fields = ['id', 'registration_token', 'device_type', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']
