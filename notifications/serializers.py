from rest_framework import serializers
from .models import Notification, VendorNotification, FCMDevice, SupportThread, SupportMessage

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


# ==============================================================================
# 1-ON-1 HELP & SUPPORT CHAT SERIALIZERS
# ==============================================================================

class SupportMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportMessage
        fields = ['id', 'thread', 'sender', 'sender_name', 'is_staff_reply', 'body', 'is_read', 'created_at']
        read_only_fields = ['id', 'thread', 'sender', 'sender_name', 'is_staff_reply', 'is_read', 'created_at']

    def get_sender_name(self, obj):
        if obj.is_staff_reply:
            return 'Support Team'
        return obj.sender.get_full_name() or obj.sender.username or obj.sender.email


class SupportThreadSerializer(serializers.ModelSerializer):
    subject_display = serializers.CharField(source='get_subject_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = SupportThread
        fields = [
            'id', 'user', 'subject', 'subject_display', 'status',
            'status_display', 'last_message', 'unread_count',
            'last_message_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'user', 'last_message_at', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        msg = obj.messages.order_by('-created_at').first()
        return msg.body if msg else ''

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_staff:
            return obj.messages.filter(is_staff_reply=False, is_read=False).count()
        return obj.messages.filter(is_staff_reply=True, is_read=False).count()
