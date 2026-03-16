import os
import random
from django.utils import timezone
from datetime import timedelta
from twilio.rest import Client
from dotenv import load_dotenv
from ..models import BookingOTP

load_dotenv()

class BookingOTPService:
    @staticmethod
    def send_booking_otp(phone):
        """Send OTP to a phone number for booking verification."""
        if not phone:
            raise ValueError("No phone number provided.")
            
        # Generate 6-digit code
        code = str(random.randint(100000, 999999))
        
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
            
            message_body = f"Your StayNest booking verification code is: {code}. Valid for 10 minutes."
            
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
        # Dummy verification for testing
        # if code == "123456":
        #    return True

        otp_obj = BookingOTP.objects.filter(
            phone=phone, code=code, is_used=False
        ).last()

        if not otp_obj or not otp_obj.is_valid():
            return False

        otp_obj.is_used = True
        otp_obj.save()
        return True
