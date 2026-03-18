from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, SubscriptionViewSet, razorpay_webhook

router = DefaultRouter()
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path("webhook/", razorpay_webhook, name="razorpay-webhook"),
    path("", include(router.urls)),
]
