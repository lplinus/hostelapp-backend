from django.conf import settings
from django.db import models
from bookings.models import Booking
from publicpages.models import PricingPlan


class Payment(models.Model):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="payment"
    )

    provider = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50)

    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.provider} - {self.transaction_id}"


class Subscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    plan = models.ForeignKey(PricingPlan, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Dummy order details
    transaction_id = models.CharField(max_length=255, unique=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"