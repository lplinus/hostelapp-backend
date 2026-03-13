from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register("subscriptions", SubscriptionViewSet, basename="subscription")
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path("", include(router.urls)),
]
