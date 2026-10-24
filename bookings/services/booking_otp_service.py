import os
import secrets
import logging
from django.utils import timezone
from datetime import timedelta
from twilio.rest import Client
from dotenv import load_dotenv
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from ..models import BookingOTP

load_dotenv()
logger = logging.getLogger(__name__)

class BookingOTPService:
    @staticmethod
    def send_booking_otp(phone):
        """Send OTP to a phone number for booking verification."""
        if not phone:
            raise ValueError("No phone number provided.")
            
        # Generate secure 6-digit code
        code = f"{secrets.randbelow(1000000):06d}"
        
        # Save to database
        otp_obj = BookingOTP.objects.create(
            phone=phone,
            code=code
        )

        # --- TWILIO SMS INTEGRATION ---
        try:
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            from_number = os.getenv('TWILIO_FROM_NUMBER')
            
            if not account_sid or not auth_token or not from_number:
                print("DEBUG: Twilio credentials missing, using console fallback")
                print(f"DEBUG: Booking OTP for {phone} is {code}")
                return code

            client = Client(account_sid, auth_token)
            
            message_body = f"Your Hostel In booking verification code is: {code}. Valid for 10 minutes."
            
            # Ensure phone has + prefix
            to_phone = phone
            if len(to_phone) == 10 and not to_phone.startswith('+'):
                to_phone = "+91" + to_phone 
            elif not to_phone.startswith('+') and not to_phone.startswith('0'):
                 to_phone = "+" + to_phone
            
            client.messages.create(
                body=message_body,
                from_=from_number,
                to=to_phone
            )
            print(f"Twilio SMS sent to {to_phone}")
        except Exception as e:
            print(f"CRITICAL TWILIO ERROR: {e}")
            print(f"DEBUG: Booking OTP for {phone} is {code}")
            
        return code

    @staticmethod
    def verify_booking_otp(phone, code):
        """Verify the OTP provided for a phone number."""
        otp_obj = BookingOTP.objects.filter(
            phone=phone, code=code, is_used=False
        ).last()

        if not otp_obj or not otp_obj.is_valid():
            return False

        otp_obj.is_used = True
        otp_obj.save()
        return True

    @staticmethod
    def send_booking_email_otp(email, guest_name=None):
        """Send OTP to an email address for booking verification."""
        if not email:
            raise ValueError("No email address provided.")
            
        clean_email = email.strip().lower()
        code = f"{secrets.randbelow(1000000):06d}"
        
        # Save to database
        BookingOTP.objects.create(
            email=clean_email,
            code=code
        )

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

        brevo_config = getattr(settings, 'BREVO_EMAIL_CONFIG', {})
        from_email = getattr(settings, 'BREVO_FROM_EMAIL', getattr(settings, 'DEFAULT_FROM_EMAIL', 'support@hostelin.online'))

        try:
            connection = get_connection(
                host=brevo_config.get('EMAIL_HOST', getattr(settings, 'EMAIL_HOST', 'smtp-relay.brevo.com')),
                port=brevo_config.get('EMAIL_PORT', getattr(settings, 'EMAIL_PORT', 587)),
                username=brevo_config.get('EMAIL_HOST_USER', getattr(settings, 'EMAIL_HOST_USER', '')),
                password=brevo_config.get('EMAIL_HOST_PASSWORD', getattr(settings, 'EMAIL_HOST_PASSWORD', '')),
                use_tls=brevo_config.get('EMAIL_USE_TLS', getattr(settings, 'EMAIL_USE_TLS', True)),
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
            print(f"DEBUG: Booking Email OTP sent to {clean_email}")
        except Exception as e:
            print(f"CRITICAL EMAIL OTP ERROR: {e}")
            print(f"DEBUG: Booking Email OTP for {clean_email} is {code}")

        return code

    @staticmethod
    def verify_booking_email_otp(email, code):
        """Verify the OTP provided for an email address."""
        if not email or not code:
            return False

        clean_email = email.strip().lower()
        clean_code = str(code).strip()

        otp_obj = BookingOTP.objects.filter(
            email__iexact=clean_email, code=clean_code, is_used=False
        ).last()

        if not otp_obj or not otp_obj.is_valid():
            return False

        otp_obj.is_used = True
        otp_obj.save()
        return True
