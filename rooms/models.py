from django.db import models
from hostels.models import Hostel
from django.utils import timezone
from Hbackend.base_models import SoftDeleteModel


class RoomType(SoftDeleteModel):
    SHARING_CHOICES = [
        (0, "Private Room"),
        (1, "Single Sharing"),
        (2, "Double Sharing"),
        (3, "Triple Sharing"),
        (4, "Four Sharing"),
        # (5, "Five Sharing"),
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

    base_price = models.DecimalField(
        null=True, blank=True, max_digits=10, decimal_places=2
    )
    price_per_day = models.DecimalField(
        null=True, blank=True, max_digits=10, decimal_places=2
    )

    is_available = models.BooleanField(default=True)
    show_this_price = models.BooleanField(
        default=False, help_text="Show this room type's price on the hostel card"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["base_price"]
        unique_together = ("hostel", "room_category", "sharing_type")

    def save(self, *args, **kwargs):
        # We need to save first to make sure this instance has a PK
        # and so that it exists in the query below if newly created.
        super().save(*args, **kwargs)
        
        # If this room type is set to show its price, ensure others are set to False
        if self.show_this_price:
            RoomType.objects.filter(hostel=self.hostel).exclude(pk=self.pk).update(show_this_price=False)
            
        # Trigger update of the hostel's price
        self.hostel.update_price_from_rooms()

    def __str__(self):
        return f"{self.hostel.name} - {self.get_room_category_display()} - {self.get_sharing_type_display()}"


class Bed(SoftDeleteModel):
    room_type = models.ForeignKey(
        RoomType, on_delete=models.CASCADE, related_name="beds"
    )
    total_beds = models.IntegerField(null=True, blank=True)
    beds_available = models.IntegerField(null=True, blank=True)
    bed_number = models.TextField(null=True, blank=True, help_text="Comma-separated bed numbers, e.g., B1, B2, B3")
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return (
            f"{self.room_type.hostel.name} | "
            f"{self.room_type.get_room_category_display()} | "
            f"{self.room_type.get_sharing_type_display()} | "
            f"Bed {self.bed_number}"
        )
