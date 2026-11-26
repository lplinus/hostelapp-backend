from .models import Notification, VendorNotification
from .firebase import send_fcm_multicast

class NotificationService:
    @staticmethod
    def create_notification(user, title, message, notif_type, related_id=None, click_action=None):
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notif_type,
            related_object_id=str(related_id) if related_id else None
        )

        # Dispatch real-time FCM Push Notification to all active user devices
        try:
            tokens = list(
                user.fcm_devices.filter(is_active=True).values_list('registration_token', flat=True)
            )
            if tokens:
                send_fcm_multicast(
                    tokens=tokens,
                    title=title,
                    body=message,
                    data={
                        'notification_id': str(notification.id),
                        'notification_type': str(notif_type),
                        'related_id': str(related_id) if related_id else '',
                    },
                    click_action=click_action or '/notification'
                )
        except Exception:
            # Push failures must never rollback DB transactions
            pass

        return notification

    @staticmethod
    def create_vendor_notification(vendor, title, message, notif_type, related_id=None, click_action=None):
        notification = VendorNotification.objects.create(
            vendor=vendor,
            title=title,
            message=message,
            notification_type=notif_type,
            related_object_id=str(related_id) if related_id else None
        )

        # Dispatch real-time FCM Push Notification to all active vendor devices
        try:
            tokens = list(
                vendor.fcm_devices.filter(is_active=True).values_list('registration_token', flat=True)
            )
            if not tokens and getattr(vendor, 'owner', None):
                tokens = list(
                    vendor.owner.fcm_devices.filter(is_active=True).values_list('registration_token', flat=True)
                )

            if tokens:
                send_fcm_multicast(
                    tokens=tokens,
                    title=title,
                    body=message,
                    data={
                        'notification_id': str(notification.id),
                        'notification_type': str(notif_type),
                        'related_id': str(related_id) if related_id else '',
                    },
                    click_action=click_action or '/vendordashboard/notifications'
                )
        except Exception:
            # Push failures must never rollback DB transactions
            pass

        return notification
