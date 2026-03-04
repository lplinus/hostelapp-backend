from django.db import models
from hostels.models import Hostel
from django.utils import timezone


class RoomType(models.Model):
    SHARING_CHOICES = [
        (1, "Single Sharing"),
        (2, "Double Sharing"),
        (3, "Triple Sharing"),
        (4, "Four Sharing"),
        (5, "Five Sharing"),
    ]

    ROOM_CATEGORY_CHOICES = [
        ("AC", "AC"),
        ("NON_AC", "Non-AC"),
    ]

    hostel = models.ForeignKey(
        "hostels.Hostel", on_delete=models.CASCADE, related_name="room_types"
    )

    # name = models.CharField(max_length=150)
    # description = models.TextField()

    room_category = models.CharField(
        max_length=10, choices=ROOM_CATEGORY_CHOICES, default="NON_AC"
    )

    sharing_type = models.IntegerField(choices=SHARING_CHOICES, default=1)

    base_price = models.DecimalField(null=True,blank=True,max_digits=10, decimal_places=2)

    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["base_price"]
        unique_together = ("hostel", "room_category", "sharing_type")

    def __str__(self):
        return f"{self.hostel.name} - {self.get_room_category_display()} - {self.get_sharing_type_display()}"


class Bed(models.Model):
    room_type = models.ForeignKey(
        RoomType, on_delete=models.CASCADE, related_name="beds"
    )
    total_beds = models.IntegerField(null=True, blank=True)
    beds_available = models.IntegerField(null=True, blank=True)
    bed_number = models.CharField(max_length=50)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return (
            f"{self.room_type.hostel.name} | "
            f"{self.room_type.get_room_category_display()} | "
            f"{self.room_type.get_sharing_type_display()} | "
            f"Bed {self.bed_number}"
        )
