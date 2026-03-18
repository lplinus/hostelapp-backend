from django.urls import re_path
from accounts.views.auth_views import (
    RegisterView,
    LoginView,
    LogoutView,
    RefreshView,
    MeView,
    VerifyEmailView,
    SendOTPView,
    VerifyOTPView,
)

app_name = "auth"

urlpatterns = [
    re_path(r"^register/?$", RegisterView.as_view(), name="register"),
    re_path(r"^login/?$", LoginView.as_view(), name="login"),
    re_path(r"^logout/?$", LogoutView.as_view(), name="logout"),
    re_path(r"^refresh/?$", RefreshView.as_view(), name="refresh"),
    re_path(r"^me/?$", MeView.as_view(), name="me"),
    re_path(r"^verify-email/?$", VerifyEmailView.as_view(), name="verify_email"),
    re_path(r"^send-otp/?$", SendOTPView.as_view(), name="send_otp"),
    re_path(r"^verify-otp/?$", VerifyOTPView.as_view(), name="verify_otp"),
]
