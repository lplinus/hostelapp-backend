import logging
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from bookings.utils.qr_generator import generate_booking_qr
from bookings.models import BookingEmailLog

logger = logging.getLogger(__name__)


class BookingEmailService:

    @staticmethod
    def send_booking_confirmation_async(booking_id, payment_id=None):
        """
        Asynchronously dispatch booking confirmation email via Celery.
        Uses transaction.on_commit to ensure the booking record is safely
        committed in the database before the background worker picks it up.
        Includes a graceful fallback if Celery/Redis is temporarily unavailable.
        """
        from django.db import transaction

        def _dispatch():
            try:
                from bookings.tasks import send_booking_confirmation_task
                send_booking_confirmation_task.delay(str(booking_id), payment_id=payment_id)
                logger.info(f"Queued Celery email task for booking {booking_id}")
            except Exception as queue_err:
                logger.warning(
                    f"Celery queue failed ({queue_err}). Executing fallback email send."
                )
                try:
                    from bookings.models import Booking
                    booking = (
                        Booking.objects.select_related("user", "hostel", "room_type")
                        .prefetch_related("hostel__extra_charges")
                        .get(id=booking_id)
                    )
                    BookingEmailService.send_booking_confirmation(booking, payment_id=payment_id)
                except Exception as fb_err:
                    logger.error(f"Fallback email dispatch error: {fb_err}")

        transaction.on_commit(_dispatch)

    @staticmethod
    def send_booking_confirmation(booking, payment_id=None):
        """
        Send a booking confirmation email with QR code
        and track email delivery status.
        """

        hostel = booking.hostel
        room_type = booking.room_type

        try:

            # Match frontend display ID logic
            booking_id_short = str(booking.id)[:8].upper()
            display_id = f"STN-{booking_id_short}"

            # Build extra charges text for QR
            extra_charges = hostel.extra_charges.all()
            extra_charges_lines = ""
            for ec in extra_charges:
                line = f"\n{ec.get_charge_type_display()}: ₹{ec.amount}"
                if ec.description:
                    line += f" ({ec.description})"
                extra_charges_lines += line

            qr_data = (
                f"BOOKING:{display_id}\n"
                f"Name: {booking.guest_name or 'Guest'}\n"
                f"Hostel: {hostel.name}\n"
                f"Room: {room_type.get_room_category_display()}\n"
                f"Check-in: {booking.check_in}\n"
                f"Check-out: {booking.check_out}\n"
                f"Payment Method: {booking.get_payment_method_display()}\n"
                f"Payment ID: {payment_id or 'N/A'}"
                f"{extra_charges_lines}"
            )

            # Get primary or first hostel image if available
            hostel_image = None
            try:
                img_obj = hostel.images.filter(is_primary=True).first() or hostel.images.first()
                if img_obj and hasattr(img_obj, "image") and img_obj.image:
                    hostel_image = img_obj.image.url
            except Exception:
                pass

            context = {
                "booking": booking,
                "display_id": display_id,
                "name": booking.guest_name or (
                    booking.user.get_full_name() if booking.user else "Guest"
                ),
                "hostel": hostel,
                "hostel_image": hostel_image,
                "room": {
                    "room_number": f"{room_type.get_room_category_display()} - {room_type.get_sharing_type_display()}"
                },
                "check_in": booking.check_in,
                "check_out": booking.check_out,
                "payment_id": payment_id,
                "payment_method": booking.get_payment_method_display(),
                "payment_status": (
                    booking.get_payment_status_display()
                    if hasattr(booking, "get_payment_status_display")
                    else getattr(booking, "payment_status", "CONFIRMED")
                ),
                "total_price": getattr(booking, "total_price", None),
                "guests_count": getattr(booking, "guests_count", 1),
                "extra_charges": extra_charges,
            }

            subject = f"Booking Confirmed - {hostel.name}"
            from_email = getattr(settings, 'BREVO_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL)

            to_email = booking.guest_email or (
                booking.user.email if booking.user else None
            )

            if not to_email:

                logger.error(f"No email found for booking {booking.id}")

                BookingEmailLog.objects.create(
                    booking_id=booking.id,
                    email="N/A",
                    status="FAILED",
                    error_message="No email address found"
                )

                return

            html_content = render_to_string(
                "emails/booking_confirmation.html",
                context
            )

            text_content = strip_tags(html_content)

            # Establish email connection (Brevo relay)
            brevo_config = getattr(settings, 'BREVO_EMAIL_CONFIG', {})
            connection = None
            if brevo_config.get('EMAIL_HOST_USER') and brevo_config.get('EMAIL_HOST_PASSWORD'):
                try:
                    connection = get_connection(
                        host=brevo_config.get('EMAIL_HOST', 'smtp-relay.brevo.com'),
                        port=brevo_config.get('EMAIL_PORT', 587),
                        username=brevo_config.get('EMAIL_HOST_USER'),
                        password=brevo_config.get('EMAIL_HOST_PASSWORD'),
                        use_tls=brevo_config.get('EMAIL_USE_TLS', True),
                        timeout=15,
                    )
                except Exception as conn_err:
                    logger.warning(f"Failed to initialize Brevo connection: {conn_err}")

            email = EmailMultiAlternatives(
                subject,
                text_content,
                from_email,
                [to_email],
                connection=connection
            )

            email.attach_alternative(html_content, "text/html")

            # Generate and attach QR code inline for fast loading in email clients
            from email.mime.image import MIMEImage
            qr_buffer = generate_booking_qr(qr_data)
            qr_image = MIMEImage(qr_buffer.getvalue(), _subtype="png")
            qr_image.add_header('Content-ID', '<booking_qr>')
            qr_image.add_header('Content-Disposition', 'inline', filename='booking_qr.png')
            email.attach(qr_image)

            # Send email
            email.send()

            logger.info(
                f"Booking confirmation email sent to {to_email} for booking {booking.id}"
            )

            # Log SUCCESS
            BookingEmailLog.objects.create(
                booking_id=booking.id,
                email=to_email,
                status="SUCCESS"
            )

        except Exception as e:

            logger.error(
                f"Failed to send booking confirmation email for booking {booking.id}: {str(e)}"
            )

            # Log FAILED
            BookingEmailLog.objects.create(
                booking_id=booking.id,
                email=booking.guest_email or "",
                status="FAILED",
                error_message=str(e)
            )

            # Do NOT raise exception (booking must not fail)