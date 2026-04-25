from .models import Notification, VendorNotification

class NotificationService:
    @staticmethod
    def create_notification(user, title, message, notif_type, related_id=None):
        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notif_type,
            related_object_id=str(related_id) if related_id else None
        )

    @staticmethod
    def create_vendor_notification(vendor, title, message, notif_type, related_id=None):
        return VendorNotification.objects.create(
            vendor=vendor,
            title=title,
            message=message,
            notification_type=notif_type,
            related_object_id=str(related_id) if related_id else None
        )
