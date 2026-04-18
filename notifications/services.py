from .models import Notification

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
