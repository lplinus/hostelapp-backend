import logging
from celery import shared_task
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
