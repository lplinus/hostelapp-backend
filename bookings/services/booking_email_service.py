import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from bookings.utils.qr_generator import generate_booking_qr
from bookings.models import BookingEmailLog

logger = logging.getLogger(__name__)


class BookingEmailService:

    @staticmethod
    def send_booking_confirmation(booking):
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

            qr_data = (
                f"BOOKING:{display_id}\n"
                f"Name: {booking.guest_name or 'Guest'}\n"
                f"Hostel: {hostel.name}\n"
                f"Room: {room_type.get_room_category_display()}\n"
                f"Check-in: {booking.check_in}\n"
                f"Check-out: {booking.check_out}"
            )

            context = {
                "booking": booking,
                "display_id": display_id,
                "name": booking.guest_name or (
                    booking.user.get_full_name() if booking.user else "Guest"
                ),
                "hostel": hostel,
                "room": {
                    "room_number": f"{room_type.get_room_category_display()} - {room_type.get_sharing_type_display()}"
                },
                "check_in": booking.check_in,
                "check_out": booking.check_out,
            }

            subject = f"Booking Confirmed - {hostel.name}"
            from_email = settings.DEFAULT_FROM_EMAIL

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

            email = EmailMultiAlternatives(
                subject,
                text_content,
                from_email,
                [to_email]
            )

            email.attach_alternative(html_content, "text/html")

            qr_buffer = generate_booking_qr(qr_data)

            email.attach(
                "booking_qr.png",
                qr_buffer.getvalue(),
                "image/png"
            )

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