import logging
from datetime import timedelta
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from bookings.models import Booking

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="bookings.tasks.send_booking_confirmation_task",
)
def send_booking_confirmation_task(self, booking_id, payment_id=None):
    """
    Celery background task to generate QR code and send
    booking confirmation email asynchronously.
    Retries up to 3 times on transient network/SMTP failure.
    """
    from bookings.services.booking_email_service import BookingEmailService

    try:
        booking = (
            Booking.objects.select_related("user", "hostel", "room_type")
            .prefetch_related("hostel__extra_charges")
            .get(id=booking_id)
        )

        BookingEmailService.send_booking_confirmation(booking, payment_id=payment_id)
        logger.info(
            f"[Celery] Confirmation email successfully processed for booking {booking_id}"
        )
        return f"Email sent for booking {booking_id}"

    except Booking.DoesNotExist:
        logger.error(f"[Celery] Booking {booking_id} does not exist. Aborting task.")
        return f"Booking {booking_id} not found"

    except Exception as exc:
        logger.error(
            f"[Celery] Error sending confirmation email for booking {booking_id}: {exc}"
        )
        # Retry with exponential backoff on transient errors (e.g., SMTP network issues)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    name="bookings.tasks.process_booking_task",
)
def process_booking_task(self, booking_id):
    """
    Celery background task to process a newly created booking when multiple bookings
    are handled concurrently.
    
    Responsibilities:
    1. Verify booking existence and atomic status check.
    2. Handle 'visit' bookings by auto-confirming and sending confirmation notification.
    3. For confirmed stay bookings, dispatch confirmation email with QR code.
    4. Log processing metrics to avoid HTTP thread blockage during high concurrent booking volume.
    """
    from bookings.services.booking_email_service import BookingEmailService

    try:
        booking = (
            Booking.objects.select_related("user", "hostel", "room_type")
            .prefetch_related("hostel__extra_charges")
            .get(id=booking_id)
        )

        logger.info(
            f"[Celery] Processing booking {booking_id} | Type: {booking.booking_type} | Status: {booking.status}"
        )

        # For visit requests, automatically transition and notify
        if booking.booking_type == "visit":
            if booking.status != "confirmed":
                booking.status = "confirmed"
                booking.save(update_fields=["status"])
                logger.info(f"[Celery] Visit booking {booking_id} marked as confirmed.")

            # Send confirmation email asynchronously
            BookingEmailService.send_booking_confirmation(booking)
            return f"Visit booking {booking_id} processed successfully"

        # If already confirmed (e.g., pay on arrival confirmed or fast check-in)
        if booking.status == "confirmed":
            BookingEmailService.send_booking_confirmation(booking)
            return f"Confirmed booking {booking_id} processed successfully"

        # For pending stay bookings (awaiting online payment)
        logger.info(
            f"[Celery] Pending booking {booking_id} queued and verified for payment."
        )
        return f"Booking {booking_id} queued in pending state"

    except Booking.DoesNotExist:
        logger.error(f"[Celery] Booking {booking_id} does not exist.")
        return f"Booking {booking_id} not found"

    except Exception as exc:
        logger.error(f"[Celery] Error processing booking {booking_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=20,
    name="bookings.tasks.process_booking_confirmation_task",
)
def process_booking_confirmation_task(self, booking_id, payment_id=None):
    """
    Celery background task executed upon successful payment (Razorpay) or Pay at Property confirmation.
    
    Ensures that when multiple bookings complete at once, the status update,
    QR generation, and email dispatch are executed reliably in the background.
    """
    from bookings.services.booking_email_service import BookingEmailService

    try:
        with transaction.atomic():
            booking = (
                Booking.objects.select_related("user", "hostel", "room_type")
                .prefetch_related("hostel__extra_charges")
                .select_for_update()
                .get(id=booking_id)
            )

            if booking.status != "confirmed":
                booking.status = "confirmed"
                booking.save(update_fields=["status"])

        # Asynchronously send confirmation email with QR code
        BookingEmailService.send_booking_confirmation(booking, payment_id=payment_id)
        logger.info(
            f"[Celery] Booking {booking_id} confirmed and notification sent (Payment ID: {payment_id})"
        )
        return f"Booking {booking_id} confirmed"

    except Booking.DoesNotExist:
        logger.error(f"[Celery] Booking {booking_id} does not exist.")
        return f"Booking {booking_id} not found"

    except Exception as exc:
        logger.error(f"[Celery] Error confirming booking {booking_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    name="bookings.tasks.cleanup_expired_bookings_task",
)
def cleanup_expired_bookings_task(expiry_minutes=30):
    """
    Celery task to automatically cancel stale pending bookings (e.g., abandoned online payments)
    older than `expiry_minutes`.
    
    This ensures that when multiple bookings are made simultaneously, abandoned bookings
    do not hold rooms or block other users from booking.
    """
    cutoff_time = timezone.now() - timedelta(minutes=expiry_minutes)

    stale_bookings = Booking.objects.filter(
        status="pending",
        payment_method="online",
        created_at__lt=cutoff_time,
    )

    count = stale_bookings.count()
    if count > 0:
        stale_bookings.update(status="cancelled")
        logger.info(
            f"[Celery] Cancelled {count} expired pending bookings older than {expiry_minutes} mins."
        )
    else:
        logger.info("[Celery] No expired pending bookings found.")

    return f"Cleaned up {count} expired bookings"


@shared_task(
    name="bookings.tasks.batch_process_bookings_task",
)
def batch_process_bookings_task(booking_ids):
    """
    Celery task to batch process multiple bookings concurrently.
    """
    results = {}
    for b_id in booking_ids:
        try:
            task = process_booking_task.delay(str(b_id))
            results[str(b_id)] = f"Dispatched task {task.id}"
        except Exception as e:
            results[str(b_id)] = f"Failed to dispatch: {str(e)}"
    return results

