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

    features = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated room features, e.g. 'Air conditioning included,Privacy pods with curtains,Individual lockable lockers'"
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

    # ── Date-Range Overlap Helpers ──────────────────────────────────────────
    # These use half-open intervals [check_in, check_out) with strict < / >
    # so same-day turnover (Guest A out June 5, Guest B in June 5) is allowed.

    ACTIVE_BOOKING_STATUSES = ("pending", "payment_initiated", "confirmed")

    def is_available_for_dates(self, check_in, check_out, exclude_booking_id=None):
        """
        Check if this specific bed is free for the given date range.
        Returns True if no overlapping active booking exists.
        """
        from bookings.models import Booking

        qs = Booking.objects.filter(
            room_type=self.room_type,
            status__in=self.ACTIVE_BOOKING_STATUSES,
            check_in__lt=check_out,   # existing starts before new guest leaves
            check_out__gt=check_in,   # existing ends after new guest arrives
        )
        if exclude_booking_id:
            qs = qs.exclude(pk=exclude_booking_id)
        return not qs.exists()

    @staticmethod
    def find_available_bed(room_type, check_in, check_out):
        """
        Auto-assign: find the first available bed in a room type for dates.
        Returns the Bed instance, or None if fully booked.
        """
        for bed in room_type.beds.filter(is_available=True):
            if bed.is_available_for_dates(check_in, check_out):
                return bed
        return None

    @staticmethod
    def count_available_beds(room_type, check_in, check_out):
        """
        How many beds are free in this room type for the given date range?
        Compares total active beds against number of overlapping active bookings.
        """
        from bookings.models import Booking

        total_beds_count = room_type.beds.filter(is_available=True).count()

        # If no individual bed rows exist, fall back to the counter field
        if total_beds_count == 0:
            bed_record = room_type.beds.first()
            if bed_record and bed_record.total_beds:
                total_beds_count = bed_record.total_beds
            else:
                return 0

        booked_count = Booking.objects.filter(
            room_type=room_type,
            status__in=Bed.ACTIVE_BOOKING_STATUSES,
            check_in__lt=check_out,
            check_out__gt=check_in,
        ).count()

        return max(0, total_beds_count - booked_count)

    def __str__(self):
        return (
            f"{self.room_type.hostel.name} | "
            f"{self.room_type.get_room_category_display()} | "
            f"{self.room_type.get_sharing_type_display()} | "
            f"Bed {self.bed_number}"
        )
