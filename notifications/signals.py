from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from bookings.models import Booking
from orders.models import Order
from hostels.models import Hostel
from .services import NotificationService
from .models import Notification, BroadcastNotification, VendorNotification
from accounts.models import User

# Simple in-memory state tracking to detect status transitions
booking_original_state = {}
order_original_state = {}
hostel_original_state = {}


@receiver(pre_save, sender=Booking)
def track_booking_state(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Booking.objects.get(pk=instance.pk)
            booking_original_state[instance.pk] = old_instance.status
        except Booking.DoesNotExist:
            booking_original_state[instance.pk] = None


@receiver(post_save, sender=Booking)
def notify_booking_changes(sender, instance, created, **kwargs):
    if created:
        # Notify Owner
        NotificationService.create_notification(
            user=instance.hostel.owner,
            title="New Booking Received",
            message=f"New booking from {instance.guest_name or 'a guest'} for {instance.hostel.name}.",
            notif_type=Notification.NotificationType.BOOKING,
            related_id=instance.id,
        )
        # Notify User
        if instance.user:
            NotificationService.create_notification(
                user=instance.user,
                title="Booking Placed",
                message=f"Your booking for {instance.hostel.name} has been placed.",
                notif_type=Notification.NotificationType.BOOKING,
                related_id=instance.id,
            )
    else:
        old_status = booking_original_state.get(instance.pk)
        if old_status and old_status != instance.status:
            if instance.user:
                NotificationService.create_notification(
                    user=instance.user,
                    title="Booking Status Update",
                    message=f"Your booking at {instance.hostel.name} is now {instance.status}.",
                    notif_type=Notification.NotificationType.BOOKING,
                    related_id=instance.id,
                )
        booking_original_state.pop(instance.pk, None)


@receiver(pre_save, sender=Order)
def track_order_state(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Order.objects.get(pk=instance.pk)
            order_original_state[instance.pk] = old_instance.status
        except Order.DoesNotExist:
            pass


@receiver(post_save, sender=Order)
def notify_order_changes(sender, instance, created, **kwargs):
    hostel_owner = instance.hostel.owner
    vendor_profile = instance.vendor

    if created:
        # Notify Vendor (Totally Separate System)
        NotificationService.create_vendor_notification(
            vendor=vendor_profile,
            title="New Order Received",
            message=f"Received order #{instance.id} from {instance.hostel.name}.",
            notif_type=VendorNotification.NotificationType.ORDER,
            related_id=instance.id,
        )
        # Notify Owner (Improved confirmation)
        NotificationService.create_notification(
            user=hostel_owner,
            title="Order Placed Successfully",
            message=f"Your order #{instance.id} has been sent to {instance.vendor.business_name}. We'll notify you when they start processing it.",
            notif_type=Notification.NotificationType.ORDER,
            related_id=instance.id,
        )
    else:
        old_status = order_original_state.get(instance.pk)
        if old_status and old_status != instance.status:
            # Notify Owner of any status change (Improved)
            NotificationService.create_notification(
                user=hostel_owner,
                title="Order Status Updated",
                message=f"Your order #{instance.id} with {instance.vendor.business_name} is now {instance.status.upper()}.",
                notif_type=Notification.NotificationType.ORDER,
                related_id=instance.id,
            )
            
            # Notify Vendor if order is cancelled or modified significantly
            if instance.status == 'cancelled':
                NotificationService.create_vendor_notification(
                    vendor=vendor_profile,
                    title="Order Cancelled",
                    message=f"Order #{instance.id} from {instance.hostel.name} has been cancelled.",
                    notif_type=VendorNotification.NotificationType.ORDER,
                    related_id=instance.id,
                )
        order_original_state.pop(instance.pk, None)


@receiver(pre_save, sender=Hostel)
def track_hostel_state(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_hostel = Hostel.objects.get(pk=instance.pk)
            hostel_original_state[instance.pk] = old_hostel.is_approved
        except Hostel.DoesNotExist:
            pass


@receiver(post_save, sender=Hostel)
def notify_hostel_approval(sender, instance, created, **kwargs):
    if not created:
        old_approval = hostel_original_state.get(instance.pk)
        if old_approval is False and instance.is_approved is True:
            NotificationService.create_notification(
                user=instance.owner,
                title="Hostel Approved!",
                message=f"Your hostel '{instance.name}' has been approved and is now live.",
                notif_type=Notification.NotificationType.HOSTEL,
                related_id=instance.id,
            )
        hostel_original_state.pop(instance.pk, None)


@receiver(post_save, sender=BroadcastNotification)
def process_broadcast_notification(sender, instance, created, **kwargs):
    if created and not instance.is_processed:
        # Create a SYSTEM notification for all active users
        users = User.objects.filter(is_active=True)
        notifications_to_create = []
        for user in users:
            notifications_to_create.append(
                Notification(
                    user=user,
                    title=instance.title,
                    message=instance.message,
                    notification_type=Notification.NotificationType.SYSTEM,
                    related_object_id=instance.link if instance.link else "broadcast",
                )
            )

        # Bulk create for efficiency
        if notifications_to_create:
            Notification.objects.bulk_create(notifications_to_create, batch_size=500)

        instance.is_processed = True
        instance.save(update_fields=["is_processed"])
