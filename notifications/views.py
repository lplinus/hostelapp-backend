from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification, VendorNotification, FCMDevice, SupportThread, SupportMessage
from .serializers import (
    NotificationSerializer,
    VendorNotificationSerializer,
    FCMDeviceSerializer,
    SupportThreadSerializer,
    SupportMessageSerializer,
)

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    User (Owner) can view their notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['patch'], url_path='read')
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        updated_count = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': 'all marked as read', 'updated_count': updated_count})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})

    @action(detail=False, methods=['delete'], url_path='clear-all')
    def clear_all(self, request):
        self.get_queryset().delete()
        return Response({'status': 'all notifications cleared'}, status=status.HTTP_204_NO_CONTENT)

class VendorNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Dedicated viewset for Vendor-specific notifications.
    """
    serializer_class = VendorNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        # Return notifications for the vendor profile owned by this user
        return VendorNotification.objects.filter(vendor__owner=self.request.user)

    @action(detail=True, methods=['patch'], url_path='read')
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        updated_count = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'status': 'all marked as read', 'updated_count': updated_count})

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})

    @action(detail=False, methods=['delete'], url_path='clear-all')
    def clear_all(self, request):
        self.get_queryset().delete()
        return Response({'status': 'all notifications cleared'}, status=status.HTTP_204_NO_CONTENT)


class FCMDeviceViewSet(viewsets.GenericViewSet):
    """
    Endpoints for registering and managing client FCM push tokens.
    Supports Web browsers, iOS, and Android clients.
    """
    serializer_class = FCMDeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        token = request.data.get('registration_token')
        device_type = request.data.get('device_type', FCMDevice.DeviceType.WEB)

        if not token:
            return Response({'error': 'registration_token is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Upsert device token for this user
        vendor_profile = getattr(request.user, 'vendor_profile', None)
        device, created = FCMDevice.objects.update_or_create(
            registration_token=token,
            defaults={
                'user': request.user,
                'vendor': vendor_profile,
                'device_type': device_type,
                'is_active': True,
            }
        )
        return Response({
            'status': 'device registered',
            'id': device.id,
            'device_type': device.device_type,
            'created': created
        }, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='deactivate')
    def deactivate(self, request):
        token = request.data.get('registration_token')
        if not token:
            return Response({'error': 'registration_token is required'}, status=status.HTTP_400_BAD_REQUEST)

        updated = FCMDevice.objects.filter(
            registration_token=token,
            user=request.user
        ).update(is_active=False)

        return Response({'status': 'device deactivated', 'updated_count': updated})


# ==============================================================================
# 1-ON-1 HELP & SUPPORT CHAT VIEWSET (REST + POLLING, NO CHANNELS)
# ==============================================================================

class SupportThreadViewSet(viewsets.ModelViewSet):
    """
    Owner / Staff 1-on-1 support chat threads & messages over standard REST.
    """
    serializer_class = SupportThreadSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return SupportThread.objects.all().prefetch_related('messages')
        return SupportThread.objects.filter(user=user).prefetch_related('messages')

    def create(self, request, *args, **kwargs):
        subject = request.data.get('subject', SupportThread.Subject.OTHER)
        initial_message = (request.data.get('message') or '').strip()
        if not initial_message:
            return Response({'error': 'message is required.'}, status=status.HTTP_400_BAD_REQUEST)

        thread = SupportThread.objects.create(
            user=request.user,
            subject=subject,
            last_message_at=timezone.now(),
        )
        SupportMessage.objects.create(
            thread=thread,
            sender=request.user,
            is_staff_reply=False,
            body=initial_message,
        )
        serializer = self.get_serializer(thread)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='messages')
    def list_messages(self, request, pk=None):
        thread = self.get_object()
        # Mark incoming messages as read
        if request.user.is_staff and thread.user != request.user:
            thread.messages.filter(is_staff_reply=False, is_read=False).update(is_read=True)
        else:
            thread.messages.filter(is_staff_reply=True, is_read=False).update(is_read=True)

        msgs = thread.messages.select_related('sender').order_by('created_at')
        return Response(SupportMessageSerializer(msgs, many=True).data)

    @action(detail=True, methods=['post'], url_path='send')
    def send_message(self, request, pk=None):
        thread = self.get_object()
        body = (request.data.get('body') or '').strip()
        if not body:
            return Response({'error': 'body is required.'}, status=status.HTTP_400_BAD_REQUEST)

        is_staff = bool(request.user.is_staff and thread.user != request.user)
        msg = SupportMessage.objects.create(
            thread=thread,
            sender=request.user,
            is_staff_reply=is_staff,
            body=body,
        )
        thread.last_message_at = timezone.now()
        if thread.status == SupportThread.Status.CLOSED:
            thread.status = SupportThread.Status.OPEN
        thread.save(update_fields=['last_message_at', 'status', 'updated_at'])

        return Response(SupportMessageSerializer(msg).data, status=status.HTTP_201_CREATED)
