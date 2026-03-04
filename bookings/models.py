from django.db import models

# Create your models here.
from django.db import models
from accounts.models import User
from hostels.models import Hostel
from rooms.models import RoomType
import uuid


class Booking(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    room_type = models.ForeignKey(
        RoomType,
        on_delete=models.CASCADE,
        related_name="bookings"
    )

    check_in = models.DateField()
    check_out = models.DateField()
    guests_count = models.IntegerField()

    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)