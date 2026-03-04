from django.db import models

# Create your models here.
from django.db import models
from bookings.models import Booking


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
        return self.transaction_id