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
    """POST /api/auth/login/ — Authenticate and return tokens."""

    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = AuthService.get_tokens_for_user(user)

        response = Response(
            {
                "access": tokens["access"],
                "user": UserProfileSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

        # Set tokens as HttpOnly cookies so user stays logged in across refreshes
        AuthService.set_refresh_cookie(response, tokens["refresh"])
        AuthService.set_access_cookie(response, tokens["access"])

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

        # Clear CSRF cookie
        response.delete_cookie("csrftoken", path="/", samesite="Lax")

        return response


class RefreshView(APIView):
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
            return Response(
                {"detail": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        response = Response(
            {"access": tokens["access"]},
            status=status.HTTP_200_OK,
        )

        # Rotate: set the new refresh + access token cookies
        AuthService.set_refresh_cookie(response, tokens["refresh"])
        AuthService.set_access_cookie(response, tokens["access"])

        return response


class MeView(APIView):
    """GET /api/auth/me/ — Return the current authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            UserProfileSerializer(request.user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
