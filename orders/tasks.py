import logging
from decimal import Decimal
from celery import shared_task
from django.db import transaction
from django.db.models import F
from orders.models import Order, OrderItem
from marketplace.models import Product

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    name="orders.tasks.process_order_creation_task",
)
def process_order_creation_task(self, order_id):
    """
    Celery background task to process a newly created order with many items
    and handle high-concurrency order surges across many users.

    Responsibilities:
    1. Verify order existence and prefetch items snapshot and products.
    2. Atomically decrement stock for products with finite inventory.
    3. Asynchronously create in-app notifications for both Vendor and Hostel Owner.
    4. Log metrics to ensure HTTP threads are never blocked.
    """
    from notifications.services import NotificationService
    from notifications.models import Notification, VendorNotification

    try:
        order = (
            Order.objects.select_related("hostel__owner", "vendor__owner")
            .prefetch_related("items__product")
            .get(id=order_id)
        )

        item_count = order.items.count()
        logger.info(
            f"[Celery] Processing order creation: Order #{order_id} | Type: {order.order_type} | Items: {item_count}"
        )

        # 1. Atomic inventory deduction for items with finite stock
        with transaction.atomic():
            for item in order.items.all():
                if item.product and item.product.stock is not None:
                    Product.objects.filter(
                        id=item.product_id, 
                        stock__gte=item.quantity
                    ).update(stock=F("stock") - item.quantity)

        # 2. Asynchronous Notifications
        hostel_owner = order.hostel.owner
        vendor_profile = order.vendor

        # Notify Vendor
        NotificationService.create_vendor_notification(
            vendor=vendor_profile,
            title="New Order Received",
            message=f"Received order #{order.id} from {order.hostel.name} ({item_count} items).",
            notif_type=VendorNotification.NotificationType.ORDER,
            related_id=order.id,
        )

        # Notify Hostel Owner
        NotificationService.create_notification(
            user=hostel_owner,
            title="Order Placed Successfully",
            message=f"Your order #{order.id} has been sent to {order.vendor.business_name}. We'll notify you when they start processing it.",
            notif_type=Notification.NotificationType.ORDER,
            related_id=order.id,
        )

        logger.info(f"[Celery] Order #{order_id} processed successfully via Celery.")
        return f"Order #{order_id} with {item_count} items processed successfully"

    except Order.DoesNotExist:
        logger.error(f"[Celery] Order #{order_id} does not exist. Aborting task.")
        return f"Order #{order_id} not found"
    except Exception as exc:
        logger.error(f"[Celery] Error processing order #{order_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    name="orders.tasks.process_order_status_update_task",
)
def process_order_status_update_task(self, order_id, old_status, new_status):
    """
    Celery background task to handle status updates, stock restoration on cancellation,
    and async notification dispatch.
    """
    from notifications.services import NotificationService
    from notifications.models import Notification, VendorNotification

    try:
        order = (
            Order.objects.select_related("hostel__owner", "vendor__owner")
            .prefetch_related("items__product")
            .get(id=order_id)
        )

        logger.info(
            f"[Celery] Processing order status transition: Order #{order_id} | {old_status} -> {new_status}"
        )

        # If cancelled, restore stock for products with finite stock
        if (
            new_status == Order.StatusChoices.CANCELLED
            and old_status != Order.StatusChoices.CANCELLED
        ):
            with transaction.atomic():
                for item in order.items.all():
                    if item.product and item.product.stock is not None:
                        Product.objects.filter(id=item.product_id).update(
                            stock=F("stock") + item.quantity
                        )
            logger.info(f"[Celery] Restored inventory stock for cancelled Order #{order_id}")

        hostel_owner = order.hostel.owner
        vendor_profile = order.vendor

        # Notify Owner
        NotificationService.create_notification(
            user=hostel_owner,
            title="Order Status Updated",
            message=f"Your order #{order.id} with {order.vendor.business_name} is now {new_status.upper()}.",
            notif_type=Notification.NotificationType.ORDER,
            related_id=order.id,
        )

        # Notify Vendor on cancellation
        if new_status == Order.StatusChoices.CANCELLED:
            NotificationService.create_vendor_notification(
                vendor=vendor_profile,
                title="Order Cancelled",
                message=f"Order #{order.id} from {order.hostel.name} has been cancelled.",
                notif_type=VendorNotification.NotificationType.ORDER,
                related_id=order.id,
            )

        logger.info(f"[Celery] Order #{order_id} status update notifications sent.")
        return f"Order #{order_id} status transition to {new_status} processed"

    except Order.DoesNotExist:
        logger.error(f"[Celery] Order #{order_id} does not exist. Aborting task.")
        return f"Order #{order_id} not found"
    except Exception as exc:
        logger.error(f"[Celery] Error updating order #{order_id} status: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    name="orders.tasks.batch_process_orders_task",
)
def batch_process_orders_task(order_ids):
    """
    Celery task to batch process multiple orders concurrently.
    Used when many user orders arrive simultaneously.
    """
    results = {}
    for o_id in order_ids:
        try:
            task = process_order_creation_task.delay(o_id)
            results[str(o_id)] = f"Dispatched task {task.id}"
        except Exception as e:
            results[str(o_id)] = f"Failed to dispatch: {str(e)}"
    return results
