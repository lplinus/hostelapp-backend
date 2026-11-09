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


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    ignore_result=True,
    name="bookings.tasks.send_booking_otp_sms_task",
)
def send_booking_otp_sms_task(self, phone, code):
    """
    Celery background task to dispatch Twilio SMS OTP for booking verification.
    Retries up to 3 times on transient network errors.
    """
    import os
    from twilio.rest import Client

    try:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")

        if not account_sid or not auth_token or not from_number:
            logger.warning("[Celery] Twilio credentials missing, using console fallback")
            logger.info(f"[Celery] Booking OTP for {phone} is {code}")
            return f"Console fallback for {phone}"

        client = Client(account_sid, auth_token)
        message_body = (
            f"Your Hostel In booking verification code is: {code}. Valid for 10 minutes."
        )

        to_phone = str(phone).strip()
        if len(to_phone) == 10 and not to_phone.startswith("+"):
            to_phone = "+91" + to_phone
        elif not to_phone.startswith("+") and not to_phone.startswith("0"):
            to_phone = "+" + to_phone

        client.messages.create(
            body=message_body,
            from_=from_number,
            to=to_phone,
        )
        logger.info(f"[Celery] Twilio SMS OTP sent successfully to {to_phone}")
        return f"Twilio SMS sent to {to_phone}"

    except Exception as exc:
        logger.error(f"[Celery] Error sending SMS OTP to {phone}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    ignore_result=True,
    name="bookings.tasks.send_booking_otp_email_task",
)
def send_booking_otp_email_task(self, email, code, guest_name=None):
    """
    Celery background task to dispatch Email OTP for booking verification via Brevo / SMTP.
    Retries up to 3 times on transient network/SMTP failures.
    """
    from django.conf import settings
    from django.core.mail import EmailMultiAlternatives, get_connection

    clean_email = email.strip().lower()
    subject = "Hostel In - Booking Verification Code"
    name_display = guest_name or "Guest"

    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; }}
        .card {{ max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,0.04); }}
        .header {{ background: #003580; padding: 24px; text-align: center; color: #ffffff; }}
        .header h1 {{ margin: 0; font-size: 20px; font-weight: 800; letter-spacing: 1px; }}
        .body {{ padding: 32px 24px; text-align: center; }}
        .title {{ font-size: 20px; font-weight: 700; color: #0f172a; margin-bottom: 8px; }}
        .desc {{ font-size: 14px; color: #64748b; line-height: 1.5; margin-bottom: 24px; }}
        .otp-box {{ display: inline-block; background: #f0f7ff; border: 2px dashed #003580; color: #003580; font-size: 32px; font-weight: 800; letter-spacing: 8px; padding: 14px 28px; border-radius: 12px; margin: 12px 0; font-family: monospace; }}
        .expiry {{ font-size: 12px; color: #94a3b8; margin-top: 12px; }}
        .footer {{ background: #f8fafc; padding: 16px 24px; text-align: center; font-size: 11px; color: #94a3b8; border-top: 1px solid #f1f5f9; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="header">
          <h1>HOSTEL IN</h1>
        </div>
        <div class="body">
          <div class="title">Verify Your Email Address</div>
          <div class="desc">Hi {name_display}, use the 6-digit verification code below to verify your email and complete your booking.</div>
          <div class="otp-box">{code}</div>
          <div class="expiry">This code is valid for 10 minutes. Please do not share this code with anyone.</div>
        </div>
        <div class="footer">
          If you did not request this booking verification, please ignore this email.<br>&copy; 2026 Hostel In. All rights reserved.
        </div>
      </div>
    </body>
    </html>
    """
    plain_message = f"Hi {name_display},\n\nYour Hostel In booking verification code is: {code}\nThis code is valid for 10 minutes.\n\nHostel In Team"

    brevo_config = getattr(settings, "BREVO_EMAIL_CONFIG", {})
    from_email = getattr(
        settings,
        "BREVO_FROM_EMAIL",
        getattr(settings, "DEFAULT_FROM_EMAIL", "support@hostelin.online"),
    )

    try:
        connection = get_connection(
            host=brevo_config.get(
                "EMAIL_HOST", getattr(settings, "EMAIL_HOST", "smtp-relay.brevo.com")
            ),
            port=brevo_config.get(
                "EMAIL_PORT", getattr(settings, "EMAIL_PORT", 587)
            ),
            username=brevo_config.get(
                "EMAIL_HOST_USER", getattr(settings, "EMAIL_HOST_USER", "")
            ),
            password=brevo_config.get(
                "EMAIL_HOST_PASSWORD", getattr(settings, "EMAIL_HOST_PASSWORD", "")
            ),
            use_tls=brevo_config.get(
                "EMAIL_USE_TLS", getattr(settings, "EMAIL_USE_TLS", True)
            ),
        )
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=[clean_email],
            connection=connection,
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
        logger.info(f"[Celery] Booking Email OTP sent successfully to {clean_email}")
        return f"Email OTP sent to {clean_email}"

    except Exception as exc:
        logger.error(f"[Celery] Error sending Email OTP to {clean_email}: {exc}")
        raise self.retry(exc=exc)


