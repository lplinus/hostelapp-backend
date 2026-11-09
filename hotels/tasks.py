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
    HotelBooking,
    HotelRoomType,
    HotelPayment,
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
    name="hotels.tasks.process_hotel_booking_task",
)
def process_hotel_booking_task(self, booking_id):
    """
    Celery background task executed whenever a hotel booking is created or updated.

    Responsibilities:
    1. Verify booking existence and fetch relations atomically.
    2. Build QR Code for fast check-in.
    3. Dispatch branded confirmation email with QR code inline attachment to guest.
    4. Dispatch notification alert to hotel owner.
    5. Safely handle high concurrency without blocking HTTP thread.
    """
    try:
        booking = (
            HotelBooking.objects.select_related(
                "hotel", "room_type", "user", "owner", "guest_details", "payment_details"
            )
            .get(id=booking_id)
        )

        hotel = booking.hotel
        room_type = booking.room_type
        guest = getattr(booking, "guest_details", None)
        payment = getattr(booking, "payment_details", None)

        guest_email = guest.guest_email if guest else (booking.user.email if booking.user else None)
        guest_name = guest.guest_name if guest else "Guest"
        guest_phone = guest.mobile_number if guest else "N/A"
        owner_email = (
            booking.owner.email
            if booking.owner
            else (hotel.owner.email if getattr(hotel, "owner", None) else None)
        )

        from_email = getattr(
            settings,
            "BREVO_FROM_EMAIL",
            getattr(settings, "DEFAULT_FROM_EMAIL", "support@hostelin.online"),
        )
        connection = _get_email_connection()

        logger.info(
            f"[Celery] Processing hotel booking {booking.booking_reference} | Status: {booking.status}"
        )

        # ── 1. Confirmed or Checked-in Hotel Booking ─────────────────────────
        if booking.status in [
            HotelBooking.BookingStatus.CONFIRMED,
            HotelBooking.BookingStatus.CHECKED_IN,
        ]:
            payment_method_str = (
                payment.get_payment_method_display() if payment else "Online Payment"
            )
            payment_status_str = (
                payment.get_payment_status_display() if payment else "Pending"
            )

            # Build QR Code data
            qr_data = (
                f"HOTEL_BOOKING:{booking.booking_reference}\n"
                f"Guest: {guest_name}\n"
                f"Hotel: {hotel.name}\n"
                f"Room: {room_type.name}\n"
                f"Rooms: {booking.number_of_rooms}\n"
                f"Check-in: {booking.check_in_date}\n"
                f"Check-out: {booking.check_out_date}\n"
                f"Nights: {booking.number_of_nights}\n"
                f"Total: ₹{booking.total_amount}\n"
                f"Payment: {payment_method_str} ({payment_status_str})"
            )

            # Send Guest Confirmation Email
            if guest_email:
                subject = f"Hotel Reservation Confirmed - {hotel.name} (#{booking.booking_reference})"
                html_body = f"""
                <!DOCTYPE html>
                <html>
                <head>
                  <meta charset="utf-8">
                  <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; }}
                    .card {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.04); }}
                    .header {{ background: #003580; padding: 24px; text-align: center; color: #ffffff; }}
                    .header h1 {{ margin: 0; font-size: 20px; font-weight: 800; letter-spacing: 0.5px; }}
                    .body {{ padding: 28px 24px; }}
                    .ref {{ font-size: 13px; font-weight: 700; color: #003580; background: #EEF2FF; padding: 6px 12px; border-radius: 8px; display: inline-block; margin-bottom: 16px; }}
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
                      <h1>HOSTEL IN • HOTELS</h1>
                    </div>
                    <div class="body">
                      <span class="ref">Reservation #{booking.booking_reference}</span>
                      <div class="title">Your hotel booking is confirmed!</div>
                      <p style="font-size: 13px; color: #64748b; line-height: 1.5; margin-bottom: 20px;">
                        Hi {guest_name}, your stay at <strong>{hotel.name}</strong> has been successfully booked.
                      </p>

                      <div class="detail-row"><span>Hotel:</span><strong>{hotel.name}</strong></div>
                      <div class="detail-row"><span>Room Type:</span><strong>{room_type.name} ({booking.number_of_rooms} Room{'s' if booking.number_of_rooms > 1 else ''})</strong></div>
                      <div class="detail-row"><span>Check-in:</span><strong>{booking.check_in_date}</strong></div>
                      <div class="detail-row"><span>Check-out:</span><strong>{booking.check_out_date}</strong></div>
                      <div class="detail-row"><span>Length of Stay:</span><strong>{booking.number_of_nights} Night(s)</strong></div>
                      <div class="detail-row"><span>Address:</span><strong>{hotel.address or (hotel.city.name if hotel.city else 'Address shared upon check-in')}</strong></div>
                      <div class="detail-row"><span>Payment:</span><strong>{payment_method_str} ({payment_status_str})</strong></div>
                      <div class="detail-row"><span>Grand Total:</span><strong style="color: #003580; font-size: 15px;">₹{booking.total_amount}</strong></div>

                      <div class="qr-container">
                        <p style="font-size: 11px; font-weight: 700; color: #475569; text-transform: uppercase; margin: 0 0 8px;">Fast Check-in Pass (Scan at Front Desk)</p>
                        <img src="cid:hotel_qr" alt="Check-in QR" style="width: 150px; height: 150px; display: inline-block;" />
                      </div>
                    </div>
                    <div class="footer">
                      Hostel In Hotels • Need help? Contact support@hostelin.online
                    </div>
                  </div>
                </body>
                </html>
                """
                plain_body = (
                    f"Hi {guest_name},\n\n"
                    f"Your booking for {hotel.name} (#{booking.booking_reference}) is confirmed.\n"
                    f"Room: {room_type.name} ({booking.number_of_rooms} Room(s))\n"
                    f"Check-in: {booking.check_in_date}\n"
                    f"Check-out: {booking.check_out_date}\n"
                    f"Total: ₹{booking.total_amount}\n"
                    f"Payment: {payment_method_str}\n\n"
                    f"Hostel In Hotels Team"
                )

                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_body,
                    from_email=from_email,
                    to=[guest_email],
                    connection=connection,
                )
                msg.attach_alternative(html_body, "text/html")

                qr_buffer = generate_booking_qr(qr_data)
                qr_img = MIMEImage(qr_buffer.getvalue(), _subtype="png")
                qr_img.add_header("Content-ID", "<hotel_qr>")
                qr_img.add_header("Content-Disposition", "inline", filename="hotel_qr.png")
                msg.attach(qr_img)

                msg.send(fail_silently=False)
                logger.info(f"[Celery] Hotel confirmation email sent to guest {guest_email}")

            # Send Hotel Owner Alert Email
            if owner_email:
                owner_subject = f"New Hotel Reservation: {hotel.name} (#{booking.booking_reference})"
                owner_body = (
                    f"Hi Hotel Manager / Owner,\n\n"
                    f"You have a new confirmed reservation for '{hotel.name}'.\n\n"
                    f"Booking Reference: #{booking.booking_reference}\n"
                    f"Guest: {guest_name} ({guest_email}, {guest_phone})\n"
                    f"Room Type: {room_type.name} ({booking.number_of_rooms} rooms)\n"
                    f"Dates: {booking.check_in_date} to {booking.check_out_date} ({booking.number_of_nights} nights)\n"
                    f"Total Amount: ₹{booking.total_amount}\n\n"
                    f"Please check your hotel dashboard to manage this booking.\n\n"
                    f"Hostel In Team"
                )
                owner_msg = EmailMultiAlternatives(
                    subject=owner_subject,
                    body=owner_body,
                    from_email=from_email,
                    to=[owner_email],
                    connection=connection,
                )
                owner_msg.send(fail_silently=True)

            return f"Hotel booking {booking.booking_reference} confirmed and notifications dispatched."

        # ── 2. Pending Hotel Booking ─────────────────────────────────────────
        logger.info(
            f"[Celery] Hotel booking {booking.booking_reference} is in status '{booking.status}'."
        )
        return f"Hotel booking {booking.booking_reference} status '{booking.status}' processed."

    except HotelBooking.DoesNotExist:
        logger.error(f"[Celery] Hotel booking {booking_id} does not exist.")
        return f"Booking {booking_id} not found"
    except Exception as exc:
        logger.error(f"[Celery] Error processing hotel booking {booking_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=20,
    ignore_result=True,
    name="hotels.tasks.send_hotel_booking_confirmation_task",
)
def send_hotel_booking_confirmation_task(self, booking_id, payment_id=None):
    """
    Celery background task executed upon payment confirmation (Razorpay) or Pay at Hotel confirmation.
    Atomically transitions status to CONFIRMED and dispatches QR confirmation task.
    """
    try:
        with transaction.atomic():
            booking = (
                HotelBooking.objects.select_for_update()
                .select_related("hotel", "room_type", "user", "owner", "guest_details", "payment_details")
                .get(id=booking_id)
            )

            if booking.status != HotelBooking.BookingStatus.CONFIRMED:
                booking.status = HotelBooking.BookingStatus.CONFIRMED
                booking.save(update_fields=["status"])

            if hasattr(booking, "payment_details") and booking.payment_details:
                if payment_id and booking.payment_details.payment_status != HotelPayment.PaymentStatus.PAID:
                    booking.payment_details.payment_status = HotelPayment.PaymentStatus.PAID
                    booking.payment_details.paid_at = timezone.now()
                    booking.payment_details.save(update_fields=["payment_status", "paid_at"])

        # Trigger confirmation email and QR dispatch asynchronously
        process_hotel_booking_task.delay(str(booking.id))
        return f"Hotel booking {booking.booking_reference} confirmed"

    except HotelBooking.DoesNotExist:
        logger.error(f"[Celery] Hotel booking {booking_id} does not exist.")
        return f"Booking {booking_id} not found"
    except Exception as exc:
        logger.error(f"[Celery] Error confirming hotel booking {booking_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    name="hotels.tasks.cleanup_expired_hotel_bookings_task",
)
def cleanup_expired_hotel_bookings_task(expiry_minutes=30):
    """
    Celery task to automatically cancel stale pending hotel bookings older than `expiry_minutes`.
    Restores room inventory for cancelled bookings to prevent blocked rooms.
    """
    cutoff_time = timezone.now() - timedelta(minutes=expiry_minutes)

    stale_bookings = HotelBooking.objects.filter(
        status=HotelBooking.BookingStatus.PENDING,
        created_at__lt=cutoff_time,
    ).select_related("room_type")

    count = 0
    for booking in stale_bookings:
        with transaction.atomic():
            booking.status = HotelBooking.BookingStatus.CANCELLED
            booking.save(update_fields=["status"])

            # Restore room inventory
            if booking.room_type:
                room_type = HotelRoomType.objects.select_for_update().get(id=booking.room_type.id)
                room_type.rooms_available += booking.number_of_rooms
                room_type.save(update_fields=["rooms_available"])

            count += 1

    if count > 0:
        logger.info(f"[Celery] Cleaned up and restored inventory for {count} expired hotel bookings.")
    else:
        logger.info("[Celery] No expired hotel bookings found.")

    return f"Cleaned up {count} expired hotel bookings"


@shared_task(
    name="hotels.tasks.batch_process_hotel_bookings_task",
)
def batch_process_hotel_bookings_task(booking_ids):
    """
    Celery task to batch process multiple hotel bookings concurrently.
    """
    results = {}
    for b_id in booking_ids:
        try:
            task = process_hotel_booking_task.delay(str(b_id))
            results[str(b_id)] = f"Dispatched task {task.id}"
        except Exception as e:
            results[str(b_id)] = f"Failed to dispatch: {str(e)}"
    return results
