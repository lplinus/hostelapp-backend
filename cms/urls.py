from django.urls import path
from .views import TermsView, PrivacyPolicyView,FAQCategoryListView,FAQListView,FAQDetailView

urlpatterns = [
    path("terms-and-conditions/", TermsView.as_view(), name="terms-and-conditions"),
    path("privacy-policy/", PrivacyPolicyView.as_view(), name="privacy-policy"),
    path("faq-categories/", FAQCategoryListView.as_view(), name="faq-categories"),
    path("faqs/", FAQListView.as_view(), name="faqs"),
    path("faqs/<str:slug>/", FAQDetailView.as_view(), name="faq-detail"),
]