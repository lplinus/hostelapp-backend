from django.urls import path
from .views import TermsView, PrivacyPolicyView

urlpatterns = [
    path("terms-and-conditions/", TermsView.as_view(), name="terms-and-conditions"),
    path("privacy-policy/", PrivacyPolicyView.as_view(), name="privacy-policy"),
]