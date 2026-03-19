from django.db import models

# Create your models here.
from django.db import models
from accounts.models import User
from hostels.models import Hostel
from rooms.models import RoomType
import uuid
from Hbackend.base_models import SoftDeleteModel


class Booking(SoftDeleteModel):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="bookings", null=True, blank=True
    )

    hostel = models.ForeignKey(
        Hostel, on_delete=models.CASCADE, related_name="bookings"
    )

    room_type = models.ForeignKey(
        RoomType, on_delete=models.CASCADE, related_name="bookings"
    )

    guest_name = models.CharField(max_length=255, blank=True, null=True)
    guest_email = models.EmailField(blank=True, null=True)
    guest_age = models.IntegerField(blank=True, null=True)
    mobile_number = models.CharField(max_length=15, blank=True, null=True)

    adults = models.IntegerField(default=1)
    children = models.IntegerField(default=0)

    check_in = models.DateField()
    check_out = models.DateField()
    guests_count = models.IntegerField()

    BOOKING_TYPE_CHOICES = (
        ("stay", "Stay"),
        ("visit", "Visit"),
    )

    STAY_DURATION_CHOICES = (
        ("none", "None"),
        ("1_month", "1 Month"),
        ("2_months", "2 Months"),
        ("3_months", "3 Months"),
        ("4_months", "4 Months"),
        ("5_months", "5 Months"),
        ("gt_5_months", "More than 5 Months"),
    )

    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    booking_type = models.CharField(max_length=10, choices=BOOKING_TYPE_CHOICES, default="stay")
    stay_duration = models.CharField(max_length=20, choices=STAY_DURATION_CHOICES, default="none", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)






#email logs

class BookingEmailLog(models.Model):

    STATUS_CHOICES = (
        ("SUCCESS", "Success"),
        ("FAILED", "Failed"),
    )

    booking_id = models.CharField(max_length=120)
    email = models.EmailField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES
    )

    error_message = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "booking_email_logs"
        ordering = ["-created_at"]


class BookingOTP(models.Model):
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.utils import timezone
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"OTP for {self.phone}"