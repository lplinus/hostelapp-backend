from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import (
    OutstandingToken,
    BlacklistedToken,
)
from rest_framework_simplejwt.exceptions import TokenError
from accounts.models import User


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
            is_active=False,  # User must verify email first
        )

        # Generate verification code for email
        v_code = VerificationCode.generate_code(user, "email")

        # Logic to send email
        AuthService.send_verification_email(user, v_code.code)

        return user

    @staticmethod
    def send_verification_email(user, code):
        """Send verification email to user."""
        from django.core.mail import send_mail
        from django.utils.html import strip_tags
        from django.template.loader import render_to_string

        subject = "Verify your account"
        message = f"Your verification code is: {code}. It will expire in 10 minutes."

        # For development debugging
        print(
            f"DEBUG: Email Verification for {user.email} is {code} (Dummy Bypass: 123456)"
        )

        # In production, use real SMTP settings
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send email: {e}")

    @staticmethod
    def send_phone_otp(user):
        """Send OTP to user's phone."""
        if not user.phone:
            raise ValueError("User does not have a phone number.")

        from accounts.models import VerificationCode

        v_code = VerificationCode.generate_code(user, "phone")

        # --- LOGIC FOR SMS OTP (COMMENTED FOR PRODUCTION USE) ---
        # import requests
        # try:
        #     # Example for SMS API (like Twilio or MSG91)
        #     # api_key = settings.SMS_API_KEY
        #     # phone = user.phone
        #     # message = f"Your Hostel App verification code is: {v_code.code}"
        #     # response = requests.post("https://api.sms-gateway.com/send", data={"key": api_key, "to": phone, "msg": message})
        #     # response.raise_for_status()
        #     print(f"SMS sent to {user.phone} with code: {v_code.code}")
        # except Exception as e:
        #     print(f"Failed to send SMS: {e}")
        # -------------------------------------------------------

        # For development, just log to console
        print(
            f"DEBUG: Phone OTP for {user.phone} is {v_code.code} (Dummy Bypass: 123456)"
        )
        return v_code.code

    @staticmethod
    def verify_code(user, code, type):
        """Verify the code provided by user."""
        from accounts.models import VerificationCode

        # --- DUMMY OTP BYPASS (Set to '123456' or '12345' for testing) ---
        # This allows developers to bypass verification during development
        if code == "123456" or code == "12345":
            if type == "email":
                user.is_email_verified = True
                user.is_active = True
            elif type == "phone":
                user.is_phone_verified = True
            user.save()
            return True
        # ----------------------------------------------------------------

        v_code = VerificationCode.objects.filter(
            user=user, code=code, type=type, is_used=False
        ).last()

        if not v_code or not v_code.is_valid():
            return False

        v_code.is_used = True
        v_code.save()

        if type == "email":
            user.is_email_verified = True
            user.is_active = True
        elif type == "phone":
            user.is_phone_verified = True

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
            max_age=7 * 24 * 60 * 60,  # 7 days
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
