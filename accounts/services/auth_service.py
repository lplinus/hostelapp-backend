from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.models import VerificationCode
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from rest_framework_simplejwt.token_blacklist.models import (
    OutstandingToken,
    BlacklistedToken,
)
from rest_framework_simplejwt.exceptions import TokenError
from accounts.models import User

from dotenv import load_dotenv
import os
from twilio.rest import Client

load_dotenv()



class AuthService:
    """
    Service layer for authentication business logic.
    Views delegate all logic here — keeps views thin.
    """

    # ───────────────────────────── REGISTER ─────────────────────────────
    @staticmethod
    def register_user(validated_data: dict) -> User:
        """Create a new user from validated serializer data."""
        from accounts.models import VerificationCode

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone=validated_data.get("phone", ""),
            role=validated_data.get("role", "guest"),
        # user.is_active = False # Commented out email activation requirement
        )
        user.is_active = False # Still False, phone verification will activate it
        user.save()

        # --- EMAIL VERIFICATION (COMMENTED OUT) ---
        # Generate verification code for email
        # v_code = VerificationCode.generate_code(user, "email")
        # AuthService.send_verification_email(user, v_code.code)

        # --- PHONE VERIFICATION (NEW PRIMARY) ---
        if user.phone:
            AuthService.send_phone_otp(user)
        
        return user

    @staticmethod
    def send_verification_email(user, code):
        """Send verification email to user (DISABLED)."""
       
        # subject = "Verify your account"
        # message = f"Your verification code is: {code}. It will expire in 10 minutes."

        # For development debugging
        print(f"DEBUG: Email Verification for {user.email} is {code} (EMAIL DISABLED)")

        # In production, use real SMTP settings
        # try:
        #     send_mail(
        #         subject,
        #         message,
        #         settings.DEFAULT_FROM_EMAIL,
        #         [user.email],
        #         fail_silently=False,
        #     )
        # except Exception as e:
        #     print(f"Failed to send email: {e}")

    @staticmethod
    def send_phone_otp(user, phone=None):
        """Send OTP to user's phone or a provided phone number."""
        target_phone = phone or user.phone
        if not target_phone:
            raise ValueError("No phone number provided.")
            
        v_code = VerificationCode.generate_code(user, "phone")

        # --- TWILIO SMS INTEGRATION ---
        try:
            account_sid = os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = os.getenv('TWILIO_AUTH_TOKEN')
            from_number = os.getenv('TWILIO_FROM_NUMBER')
            
            sid_debug = account_sid[:5] if account_sid else "MISSING"
            # print(f"DEBUG: Twilio Prep - SID: {sid_debug}..., Token: {'Loaded' if auth_token else 'Missing'}, From: {from_number}")
            
            if not account_sid or not auth_token or not from_number:
                raise ValueError("Twilio credentials missing in .env")

            client = Client(account_sid, auth_token)
            
            message_body = f"Your verification code is: {v_code.code}. It will expire in 10 minutes."
            
            # Ensure phone has + prefix for Twilio if it's just 10 digits
            to_phone = target_phone
            if len(to_phone) == 10 and not to_phone.startswith('+'):
                to_phone = "+91" + to_phone 
            elif not to_phone.startswith('+') and not to_phone.startswith('0'):
                 to_phone = "+" + to_phone
            
            # print(f"DEBUG: Attempting to send SMS to {to_phone} from {from_number}")

            message = client.messages.create(
                body=message_body,
                from_=from_number,
                to=to_phone
            )
            # print(f"Twilio SMS sent to {to_phone}: {message.sid}")
        except Exception as e:
            print(f"CRITICAL TWILIO ERROR: {e}")
            # Fallback for debugging
            # print(f"DEBUG: Phone OTP for {target_phone} is {v_code.code}")

        # --- ORIGINAL LOGIC (COMMENTED) ---
        # if not user.phone:
        #     raise ValueError("User does not have a phone number.")
        # v_code = VerificationCode.generate_code(user, "phone")
        # # ... (rest of old code)
        # print(f"DEBUG: Phone OTP for {user.phone} is {v_code.code} (Dummy Bypass: 123456)")
        
        return v_code.code





        #send_phone_otp by twilio
        #--------------------------------------------

    # --- ORIGINAL TWILIO PLACEHOLDER (COMMENTED) ---
    # @staticmethod
    # def send_otp_via_twilio(phone):
    #     account_sid = os.getenv('account_sid')
    #     auth_token = os.getenv('auth_token')
    #     client = Client(account_sid, auth_token)
    #     import random
    #     otp = str(random.randint(100000, 999999))
    #
    #     client.messages.create(
    #         body=f'Your OTP is {otp}, please do not share it with anyone.',
    #         from_='+1(582) 264-8352',
    #         to="+91" + phone
    #     )
    #     return otp


        

    @staticmethod
    def verify_code(user, code, type, phone=None):
        """Verify the code provided by user."""
        # Dummy verification for testing
        # if code == "123456":
        #     if type == "phone":
        #         user.is_phone_verified = True
        #         user.is_active = True
        #         if phone:
        #             user.phone = phone
        #         user.save()
        #     return True

        v_code = VerificationCode.objects.filter(
            user=user, code=code, type=type, is_used=False
        ).last()

        if not v_code or not v_code.is_valid():
            return False

        v_code.is_used = True
        v_code.save()

        # if type == "email":
        #     user.is_email_verified = True
        #     user.is_active = True
        # elif type == "phone":
        if type == "phone":
            user.is_phone_verified = True
            user.is_active = True # Activate user on phone verification
            if phone:
                user.phone = phone

        user.save()
        return True




    # ───────────────────────────── TOKENS ────────────────────────────────
    @staticmethod
    def get_tokens_for_user(user: User) -> dict:
        """Generate JWT access + refresh pair for a user."""
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    # ───────────────────────────── REFRESH ───────────────────────────────
    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict:
        """
        Rotate refresh token and return new access + refresh pair.
        The old refresh token is automatically blacklisted by SimpleJWT
        when ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION are enabled.
        """
        try:
            refresh = RefreshToken(refresh_token)
            new_access = str(refresh.access_token)

            # Rotation: create new refresh token
            new_refresh = str(refresh)

            return {
                "access": new_access,
                "refresh": new_refresh,
            }
        except TokenError:
            raise ValueError("Refresh token is invalid or expired.")

    # ───────────────────────────── LOGOUT ────────────────────────────────
    @staticmethod
    def blacklist_refresh_token(refresh_token: str) -> None:
        """Blacklist the given refresh token so it cannot be reused."""
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            # Already expired or blacklisted — fail silently
            pass

    # ─────────────────────── COOKIE HELPERS ──────────────────────────────
    @staticmethod
    def set_refresh_cookie(response, refresh_token: str):
        """Set the refresh token as an HttpOnly cookie on the response."""
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=not settings.DEBUG,  # True in production
            samesite="Lax",
            max_age=30 * 24 * 60 * 60,  # 30 days
            path="/",
        )
        return response

    @staticmethod
    def set_access_cookie(response, access_token: str):
        """Set the access token as an HttpOnly cookie on the response."""
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            max_age=10 * 60,  # 10 minutes (matches ACCESS_TOKEN_LIFETIME)
            path="/",
        )
        return response

    @staticmethod
    def delete_refresh_cookie(response):
        """Remove the refresh token cookie."""
        response.delete_cookie(
            key="refresh_token",
            path="/",
            samesite="Lax",
        )
        return response

    @staticmethod
    def delete_access_cookie(response):
        """Remove the access token cookie."""
        response.delete_cookie(
            key="access_token",
            path="/",
            samesite="Lax",
        )
        return response
