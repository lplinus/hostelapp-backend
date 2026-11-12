import logging
from datetime import timedelta
from decimal import Decimal
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import transaction
from django.utils import timezone
from email.mime.image import MIMEImage

from bookings.utils.qr_generator import generate_booking_qr
from .models import (
    VacationRentalBooking,
    VacationRentalAvailability,
)

logger = logging.getLogger(__name__)


def _get_email_connection():
    """Helper to initialize Brevo/SMTP connection safely from Django settings."""
    brevo_config = getattr(settings, "BREVO_EMAIL_CONFIG", {})
    if brevo_config.get("EMAIL_HOST_USER") and brevo_config.get("EMAIL_HOST_PASSWORD"):
        try:
            return get_connection(
                host=brevo_config.get("EMAIL_HOST", "smtp-relay.brevo.com"),
                port=brevo_config.get("EMAIL_PORT", 587),
                username=brevo_config.get("EMAIL_HOST_USER"),
                password=brevo_config.get("EMAIL_HOST_PASSWORD"),
                use_tls=brevo_config.get("EMAIL_USE_TLS", True),
                timeout=15,
            )
        except Exception as conn_err:
            logger.warning(f"[Celery] Failed to initialize Brevo connection: {conn_err}")
    return None


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=15,
    ignore_result=True,
    name="vacanationrentals.tasks.process_vacation_rental_booking_task",
)
def process_vacation_rental_booking_task(self, booking_id):
    """
    Celery background task executed whenever a vacation rental booking is created.
    
    Responsibilities:
    1. Verify booking existence and atomic status check.
    2. If instant-confirmed, lock calendar dates and dispatch confirmation email with QR code.
    3. If pending approval, notify the host to approve/decline and acknowledge the guest.
    4. Handles concurrent bookings safely without blocking HTTP thread.
    """
    try:
        booking = (
            VacationRentalBooking.objects.select_related(
                "rental", "user", "host", "owner", "guest_details", "pricing_details"
            )
            .get(id=booking_id)
        )

        rental = booking.rental
        guest = getattr(booking, "guest_details", None)
        pricing = getattr(booking, "pricing_details", None)

        guest_email = guest.guest_email if guest else (booking.user.email if booking.user else None)
        guest_name = guest.guest_name if guest else "Guest"
        host_email = booking.host.email if booking.host else (booking.owner.email if booking.owner else None)

        from_email = getattr(settings, "BREVO_FROM_EMAIL", getattr(settings, "DEFAULT_FROM_EMAIL", "support@hostelin.online"))
        connection = _get_email_connection()

        # ── Branch 1: Confirmed Booking (Instant Book or Pre-confirmed) ───────
        if booking.status == VacationRentalBooking.BookingStatus.CONFIRMED:
            # Block availability dates
            curr = booking.check_in_date
            while curr < booking.check_out_date:
                VacationRentalAvailability.objects.update_or_create(
                    rental=rental,
                    date=curr,
                    defaults={"is_available": False, "reason": VacationRentalAvailability.BlockReason.BOOKED},
                )
                curr += timedelta(days=1)

            # Build QR Code
            payment_method_str = pricing.get_payment_method_display() if pricing else "Online"
            qr_data = (
                f"BOOKING:{booking.booking_reference}\n"
                f"Guest: {guest_name}\n"
                f"Rental: {rental.title}\n"
                f"Check-in: {booking.check_in_date}\n"
                f"Check-out: {booking.check_out_date}\n"
                f"Nights: {booking.number_of_nights}\n"
                f"Total: ₹{booking.total_price}\n"
                f"Payment: {payment_method_str}"
            )

            # Send Guest Confirmation Email
            if guest_email:
                subject = f"Reservation Confirmed - {rental.title} (#{booking.booking_reference})"
                html_body = f"""
                <!DOCTYPE html>
                <html>
                <head>
                  <meta charset="utf-8">
                  <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; }}
                    .card {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.04); }}
                    .header {{ background: #312E81; padding: 24px; text-align: center; color: #ffffff; }}
                    .header h1 {{ margin: 0; font-size: 20px; font-weight: 800; letter-spacing: 0.5px; }}
                    .body {{ padding: 28px 24px; }}
                    .ref {{ font-size: 13px; font-weight: 700; color: #312E81; background: #EEF2FF; padding: 6px 12px; border-radius: 8px; display: inline-block; margin-bottom: 16px; }}
                    .title {{ font-size: 18px; font-weight: 800; color: #0f172a; margin-bottom: 8px; }}
                    .detail-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #f1f5f9; font-size: 13px; color: #475569; }}
                    .detail-row strong {{ color: #0f172a; }}
                    .qr-container {{ text-align: center; margin: 24px 0 16px; padding: 16px; background: #F8FAFC; border-radius: 12px; border: 1px dashed #CBD5E1; }}
                    .footer {{ background: #f8fafc; padding: 16px 24px; text-align: center; font-size: 11px; color: #94a3b8; border-top: 1px solid #f1f5f9; }}
                  </style>
                </head>
                <body>
                  <div class="card">
                    <div class="header">
                      <h1>HOSTEL IN • VACATION RENTALS</h1>
                    </div>
                    <div class="body">
                      <span class="ref">Booking #{booking.booking_reference}</span>
                      <div class="title">Your reservation is confirmed!</div>
                      <p style="font-size: 13px; color: #64748b; line-height: 1.5; margin-bottom: 20px;">
                        Hi {guest_name}, pack your bags! Your stay at <strong>{rental.title}</strong> is officially locked in.
                      </p>

                      <div class="detail-row"><span>Check-in:</span><strong>{booking.check_in_date}</strong></div>
                      <div class="detail-row"><span>Check-out:</span><strong>{booking.check_out_date}</strong></div>
                      <div class="detail-row"><span>Length of Stay:</span><strong>{booking.number_of_nights} Night(s)</strong></div>
                      <div class="detail-row"><span>Address:</span><strong>{rental.address or 'Address shared upon check-in'}</strong></div>
                      <div class="detail-row"><span>Total Paid/Payable:</span><strong style="color: #312E81; font-size: 15px;">₹{booking.total_price}</strong></div>

                      <div class="qr-container">
                        <p style="font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; margin: 0 0 8px;">Fast Check-in Pass (Scan at Arrival)</p>
                        <img src="cid:rental_qr" alt="Check-in QR" style="width: 150px; height: 150px; display: inline-block;" />
                      </div>
                    </div>
                    <div class="footer">
                      Hostel In Vacation Rentals • Need help? Contact support@hostelin.online
                    </div>
                  </div>
                </body>
                </html>
                """
                plain_body = f"Hi {guest_name},\nYour booking for {rental.title} (#{booking.booking_reference}) is confirmed.\nCheck-in: {booking.check_in_date}\nCheck-out: {booking.check_out_date}\nTotal: ₹{booking.total_price}\n\nHostel In Team"

                msg = EmailMultiAlternatives(subject=subject, body=plain_body, from_email=from_email, to=[guest_email], connection=connection)
                msg.attach_alternative(html_body, "text/html")

                qr_buffer = generate_booking_qr(qr_data)
                qr_img = MIMEImage(qr_buffer.getvalue(), _subtype="png")
                qr_img.add_header("Content-ID", "<rental_qr>")
                qr_img.add_header("Content-Disposition", "inline", filename="rental_qr.png")
                msg.attach(qr_img)

                msg.send(fail_silently=False)
                logger.info(f"[Celery] Vacation rental confirmation email sent to guest {guest_email}")

            # Send Host Alert Email
            if host_email:
                host_subject = f"New Reservation Confirmed: {rental.title} (#{booking.booking_reference})"
                host_body = f"Hi Host,\n\nYou have a new confirmed reservation for '{rental.title}'.\n\nGuest: {guest_name} ({guest_email})\nDates: {booking.check_in_date} to {booking.check_out_date} ({booking.number_of_nights} nights)\nPayout Total: ₹{booking.total_price}\n\nPlease check your host dashboard to view details.\n\nHostel In Team"
                host_msg = EmailMultiAlternatives(subject=host_subject, body=host_body, from_email=from_email, to=[host_email], connection=connection)
                host_msg.send(fail_silently=True)

            return f"Confirmed booking {booking.booking_reference} processed successfully."

        # ── Branch 2: Pending Approval Booking ────────────────────────────────
        elif booking.status == VacationRentalBooking.BookingStatus.PENDING_APPROVAL:
            if host_email:
                host_subject = f"Action Required: New Reservation Request for {rental.title}"
                host_body = f"Hi Host,\n\nYou have received a new booking request for '{rental.title}' (#{booking.booking_reference}).\n\nGuest: {guest_name}\nDates: {booking.check_in_date} to {booking.check_out_date}\nTotal: ₹{booking.total_price}\n\nPlease log in to your dashboard to review and approve this booking request.\n\nHostel In Team"
                host_msg = EmailMultiAlternatives(subject=host_subject, body=host_body, from_email=from_email, to=[host_email], connection=connection)
                host_msg.send(fail_silently=True)

            if guest_email:
                guest_subject = f"Reservation Request Received - {rental.title} (#{booking.booking_reference})"
                guest_body = f"Hi {guest_name},\n\nWe have received your reservation request for '{rental.title}'. The host has been notified to review and confirm your dates.\n\nYou will receive a confirmation email as soon as the host approves your request.\n\nHostel In Team"
                guest_msg = EmailMultiAlternatives(subject=guest_subject, body=guest_body, from_email=from_email, to=[guest_email], connection=connection)
                guest_msg.send(fail_silently=True)

            return f"Pending booking {booking.booking_reference} queued and host notified."

        return f"Booking {booking.booking_reference} status '{booking.status}' processed."

    except VacationRentalBooking.DoesNotExist:
        logger.error(f"[Celery] Vacation rental booking {booking_id} does not exist.")
        return f"Booking {booking_id} not found"
    except Exception as exc:
        logger.error(f"[Celery] Error processing vacation rental booking {booking_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=20,
    ignore_result=True,
    name="vacanationrentals.tasks.send_vacation_rental_confirmation_task",
)
def send_vacation_rental_confirmation_task(self, booking_id, payment_id=None):
    """
    Celery background task executed upon host approval or online payment verification.
    Guarantees atomic status update to CONFIRMED, calendar date locking, and email dispatch.
    """
    try:
        with transaction.atomic():
            booking = (
                VacationRentalBooking.objects.select_for_update()
                .select_related("rental", "user", "host", "guest_details", "pricing_details")
                .get(id=booking_id)
            )

            if booking.status != VacationRentalBooking.BookingStatus.CONFIRMED:
                booking.status = VacationRentalBooking.BookingStatus.CONFIRMED
                booking.save(update_fields=["status"])

            # Block availability dates in calendar
            curr = booking.check_in_date
            while curr < booking.check_out_date:
                VacationRentalAvailability.objects.update_or_create(
                    rental=booking.rental,
                    date=curr,
                    defaults={"is_available": False, "reason": VacationRentalAvailability.BlockReason.BOOKED},
                )
                curr += timedelta(days=1)

        # Trigger confirmation email dispatch via Celery task
        process_vacation_rental_booking_task.delay(str(booking.id))
        return f"Confirmation queued for booking {booking.booking_reference}"

    except VacationRentalBooking.DoesNotExist:
        logger.error(f"[Celery] Vacation rental booking {booking_id} does not exist.")
        return f"Booking {booking_id} not found"
    except Exception as exc:
        logger.error(f"[Celery] Error confirming vacation rental booking {booking_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    name="vacanationrentals.tasks.cleanup_expired_vacation_rental_bookings_task",
)
def cleanup_expired_vacation_rental_bookings_task(default_expiry_minutes=25):
    """
    Smarter cleanup logic following major platforms (Airbnb, Vrbo):
    
    Only cancels/deletes a vacation rental booking when:
    1. Status is still 'pending_approval' or 'payment_initiated'
    2. AND the booking has fully expired based on `expires_at` (or fallback cutoff_time if expires_at is null)
    
    Bookings in 'payment_initiated' status are protected until their extended +20 minute
    window (up to 45 mins total) has elapsed, ensuring users completing payment
    are not prematurely cancelled.
    Frees calendar dates for cancelled bookings.
    """
    from django.db.models import Q
    now = timezone.now()
    fallback_cutoff = now - timedelta(minutes=default_expiry_minutes)

    stale_filter = (
        Q(expires_at__isnull=False, expires_at__lte=now)
        | Q(expires_at__isnull=True, created_at__lt=fallback_cutoff)
    )

    stale_bookings = VacationRentalBooking.objects.filter(
        status__in=[
            VacationRentalBooking.BookingStatus.PENDING_APPROVAL,
            VacationRentalBooking.BookingStatus.PAYMENT_INITIATED,
        ],
    ).filter(stale_filter)

    count = 0
    for booking in stale_bookings:
        with transaction.atomic():
            booking.status = VacationRentalBooking.BookingStatus.CANCELLED
            booking.save(update_fields=["status"])

            # Free the calendar dates if previously blocked
            VacationRentalAvailability.objects.filter(
                rental=booking.rental,
                date__gte=booking.check_in_date,
                date__lt=booking.check_out_date,
                reason=VacationRentalAvailability.BlockReason.BOOKED,
            ).delete()

            count += 1

    if count > 0:
        logger.info(f"[Celery] Cancelled and released dates for {count} expired vacation rental bookings.")
    else:
        logger.info("[Celery] No expired vacation rental bookings found.")

    return f"Cleaned up {count} expired vacation rental bookings"

