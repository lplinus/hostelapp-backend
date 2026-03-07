from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.middleware.csrf import get_token

from accounts.serializers.auth_serializer import RegisterSerializer, LoginSerializer
from accounts.serializers.user_serializer import UserProfileSerializer
from accounts.services.auth_service import AuthService


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
                "message": "Account created successfully. You can now log in.",
                "user": UserProfileSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
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

        # Set refresh token as HttpOnly cookie
        AuthService.set_refresh_cookie(response, tokens["refresh"])

        from django.conf import settings

        # Set CSRF token cookie (readable by frontend JS)
        response.set_cookie(
            key="csrftoken",
            value=get_token(request),
            httponly=False,  # Must be readable by JS
            secure=settings.CSRF_COOKIE_SECURE,  # Dynamic based on env
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
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

        # Rotate: set the new refresh token cookie
        AuthService.set_refresh_cookie(response, tokens["refresh"])

        return response


class MeView(APIView):
    """GET /api/auth/me/ — Return the current authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            UserProfileSerializer(request.user, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )
