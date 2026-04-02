"""
Authentication Views for the Accounts application.
This module handles user registration, email/phone verification,
login, logout, and token refresh logic using JWT and cookies.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.middleware.csrf import get_token

from accounts.serializers.auth_serializer import (
    RegisterSerializer,
    LoginSerializer,
    VerifyEmailSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
)
from accounts.serializers.user_serializer import UserProfileSerializer
from accounts.services.auth_service import AuthService
from accounts.models import User


class RegisterView(APIView):
    """
    Handles user registration.
    POST /api/auth/register/
    Expects user data (email, password, etc.), creates a new inactive user,
    and triggers an email verification code.
    """

    """POST /api/auth/register/ — Create a new user account."""

    permission_classes = [AllowAny]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = AuthService.register_user(serializer.validated_data)

        return Response(
            {
                "message": "Account created successfully. Please check your email for the verification code.",
                "user": UserProfileSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    """
    Verifies a user's email address using a code.
    POST /api/auth/verify-email/
    Activates the user account upon successful verification.
    """

    """POST /api/auth/verify-email/ — Verify user account via email code."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if AuthService.verify_code(user, code, "email"):
            return Response(
                {"message": "Email verified successfully. You can now log in."},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"detail": "Invalid or expired code."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SendOTPView(APIView):
    """
    Sends a One-Time Password (OTP) to the user's phone for verification.
    POST /api/auth/send-otp/
    Requires the user to be authenticated.
    """

    """POST /api/auth/send-otp/ — Send OTP to authenticated user's phone."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        phone = serializer.validated_data.get("phone")

        # if not user.phone: # Old check
        #     return Response(
        #         {"detail": "Phone number not set in profile."},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )

        try:
            # AuthService.send_phone_otp(user) # Old call
            AuthService.send_phone_otp(user, phone=phone)
            return Response(
                {"message": "OTP sent successfully."}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyOTPView(APIView):
    """
    Verifies the phone OTP provided by the user.
    POST /api/auth/verify-otp/
    Updates the user's phone verification status upon success.
    """

    """POST /api/auth/verify-otp/ — Verify phone OTP."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        code = serializer.validated_data["code"]
        phone = serializer.validated_data.get("phone")

        # if AuthService.verify_code(user, code, "phone"): # Old call
        if AuthService.verify_code(user, code, "phone", phone=phone):
            return Response(
                {"message": "Phone verified successfully."}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"detail": "Invalid or expired OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LoginView(APIView):
    """
    Authenticates a user and issues JWT tokens.
    POST /api/auth/login/
    Tokens are returned in the response body (access) and set as HttpOnly cookies (access and refresh).
    Also sets a CSRF token for frontend security.
    """

    """POST /api/auth/login/ — Authenticate and return tokens."""

    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = AuthService.get_tokens_for_user(user)

        response_data = {
            "access": tokens["access"],
            "user": UserProfileSerializer(user).data,
        }

        # Redirect logic based on role
        if user.role == "vendor":
            response_data["redirect_url"] = "/vendordashboard/vendors"
        else:
            response_data["redirect_url"] = "/dashboard"

        response = Response(response_data, status=status.HTTP_200_OK)

        # Set tokens as HttpOnly cookies so user stays logged in across refreshes
        AuthService.set_refresh_cookie(response, tokens["refresh"])
        AuthService.set_access_cookie(response, tokens["access"])
        AuthService.set_role_cookie(response, user.role)

        from django.conf import settings

        # Set CSRF token cookie (readable by frontend JS)
        response.set_cookie(
            key="csrftoken",
            value=get_token(request),
            httponly=False,  # Must be readable by JS
            secure=settings.CSRF_COOKIE_SECURE,  # Dynamic based on env
            samesite="Lax",
            max_age=30 * 24 * 60 * 60,
            path="/",
        )

        return response


class LogoutView(APIView):
    """
    Logs out the user by blacklisting the refresh token and clearing relevant cookies.
    POST /api/auth/logout/
    """

    """POST /api/auth/logout/ — Blacklist refresh token and clear cookie."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")

        if refresh_token:
            AuthService.blacklist_refresh_token(refresh_token)

        response = Response(
            {"message": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )

        AuthService.delete_refresh_cookie(response)
        AuthService.delete_access_cookie(response)
        AuthService.delete_role_cookie(response)

        # Clear CSRF cookie
        response.delete_cookie("csrftoken", path="/", samesite="Lax")

        return response


class RefreshView(APIView):
    """
    Refreshes the JWT access token using the refresh token stored in cookies.
    POST /api/auth/refresh/
    Implements token rotation by issuing both a new access and a new refresh token.
    """

    """POST /api/auth/refresh/ — Issue new access token using refresh cookie."""

    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response(
                {"detail": "No refresh token found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            tokens = AuthService.refresh_access_token(refresh_token)
        except ValueError as e:
            response = Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            # Hard clear cookies if the refresh token is invalid
            AuthService.delete_refresh_cookie(response)
            AuthService.delete_access_cookie(response)
            AuthService.delete_role_cookie(response)
            return response

        response = Response(
            {"access": tokens["access"]},
            status=status.HTTP_200_OK,
        )

        # Rotate: set the new refresh + access token cookies
        AuthService.set_refresh_cookie(response, tokens["refresh"])
        AuthService.set_access_cookie(response, tokens["access"])

        return response


class MeView(APIView):
    """
    Returns the profile data of the currently authenticated user.
    GET /api/auth/me/
    """

    """GET /api/auth/me/ — Return the current authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            UserProfileSerializer(request.user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
