from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, SubscriptionViewSet, razorpay_webhook, VendorPricingPlanAPIView, VendorSubscriptionViewSet

router = DefaultRouter()
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("vendor-subscriptions", VendorSubscriptionViewSet, basename="vendor-subscription")
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path("webhook/", razorpay_webhook, name="razorpay-webhook"),
    path("vendor-plans/", VendorPricingPlanAPIView.as_view(), name="vendor-plans-api"),
    path("", include(router.urls)),
]
