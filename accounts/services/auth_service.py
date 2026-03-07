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
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            phone=validated_data.get("phone", ""),
            role=validated_data.get("role", "guest"),
        )
        return user

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
