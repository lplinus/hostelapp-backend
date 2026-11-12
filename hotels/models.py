import os
import uuid
import secrets
from decimal import Decimal
from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from Hbackend.base_models import SoftDeleteModel
from Hbackend.utils import (
    process_image_fields,
    delete_old_image_files,
    validate_image_size,
)


def hotel_image_upload_path(instance, filename):
    hotel = getattr(instance, "hotel", None)
    if not hotel and getattr(instance, "hotel_id", None):
        hotel = Hotel.objects.filter(id=instance.hotel_id).first()
    hotel_name = hotel.slug if (hotel and getattr(hotel, "slug", None)) else (slugify(hotel.name) if (hotel and getattr(hotel, "name", None)) else "hotel")
    ext = os.path.splitext(filename)[1].lower() or ".webp"
    order = getattr(instance, "order", 0) or 0
    return f"hotels/{hotel_name}/{hotel_name}-photo-{order + 1}{ext}"


class Hotel(SoftDeleteModel):
    class HotelType(models.TextChoices):
        LUXURY = "luxury", "Luxury Hotel"
        BOUTIQUE = "boutique", "Boutique Hotel"
        BUSINESS = "business", "Business Hotel"
        RESORT = "resort", "Resort & Spa"
        BUDGET = "budget", "Budget Hotel"
        HERITAGE = "heritage", "Heritage Hotel"

    class CancellationPolicy(models.TextChoices):
        FREE_CANCELLATION = "free_cancellation", "Free Cancellation (Up to 24h before check-in)"
        MODERATE = "moderate", "Moderate (Full refund up to 3 days before check-in)"
        NON_REFUNDABLE = "non_refundable", "Non-Refundable"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="hotels",
        null=True,
        blank=True,
        help_text="Hotel Owner",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    tagline = models.CharField(max_length=255, blank=True, null=True, help_text="e.g. 5-Star Waterfront Luxury")
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True, null=True)

    hotel_type = models.CharField(
        max_length=30,
        choices=HotelType.choices,
        default=HotelType.BOUTIQUE,
        db_index=True,
    )
    star_rating = models.PositiveSmallIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Official star rating (1 to 5)",
    )

    # Location
    city = models.ForeignKey("locations.City", on_delete=models.CASCADE, related_name="hotels")
    area = models.ForeignKey("locations.Area", on_delete=models.SET_NULL, null=True, blank=True, related_name="hotels")
    address = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Check-in / Check-out
    check_in_time = models.TimeField(default="14:00")
    check_out_time = models.TimeField(default="11:00")

    # Pricing summary
    starting_price_per_night = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Starting nightly rate, automatically updated from room types",
    )

    # Amenities & Policies
    amenities = models.ManyToManyField("amenities.Amenity", related_name="hotels", blank=True)
    cancellation_policy = models.CharField(
        max_length=30,
        choices=CancellationPolicy.choices,
        default=CancellationPolicy.FREE_CANCELLATION,
    )
    allows_pets = models.BooleanField(default=False)

    # Quality & Rating metrics
    rating_avg = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)
    is_featured = models.BooleanField(default=False)
    is_toprated = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)

    # SEO & Media
    og_image = models.ImageField(
        upload_to="seo/hotels/",
        max_length=500,
        null=True,
        blank=True,
        validators=[validate_image_size],
    )
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "-rating_avg", "-created_at"]

    def __str__(self):
        return f"{self.name} ({self.star_rating}★)"

    def update_starting_price(self):
        """
        Calculates and updates starting_price_per_night based on the lowest active room type.
        """
        lowest_room = self.room_types.filter(is_available=True).order_by("base_price_per_night").first()
        if lowest_room:
            self.starting_price_per_night = lowest_room.base_price_per_night
            self.save(update_fields=["starting_price_per_night"])

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Hotel.all_objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        delete_old_image_files(self, ["og_image"])
        process_image_fields(self, ["og_image"])
        super().save(*args, **kwargs)


class HotelRoomType(SoftDeleteModel):
    class RoomCategory(models.TextChoices):
        STANDARD = "standard", "Standard Room"
        DELUXE = "deluxe", "Deluxe Room"
        EXECUTIVE_SUITE = "executive_suite", "Executive Suite"
        FAMILY_SUITE = "family_suite", "Family Suite"
        PRESIDENTIAL_SUITE = "presidential_suite", "Presidential Suite"
        STUDIO = "studio", "Studio"

    class BedType(models.TextChoices):
        KING = "king", "1 King Bed"
        QUEEN = "queen", "1 Queen Bed"
        TWIN = "twin", "2 Twin Beds"
        DOUBLE = "double", "2 Double Beds"
        SINGLE = "single", "1 Single Bed"

    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="room_types")
    name = models.CharField(max_length=150, help_text="e.g. Deluxe Sea View Room")
    room_category = models.CharField(
        max_length=30,
        choices=RoomCategory.choices,
        default=RoomCategory.DELUXE,
    )
    bed_type = models.CharField(
        max_length=30,
        choices=BedType.choices,
        default=BedType.KING,
    )
    description = models.TextField(blank=True, null=True)

    # Capacity
    max_adults = models.PositiveIntegerField(default=2)
    max_children = models.PositiveIntegerField(default=1)
    max_occupancy = models.PositiveIntegerField(default=3)

    # Inventory
    total_rooms = models.PositiveIntegerField(default=1, help_text="Total count of this room type in the hotel")
    rooms_available = models.PositiveIntegerField(default=1)

    # Pricing & Inclusions
    base_price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("12.00"))
    includes_breakfast = models.BooleanField(default=False)
    is_refundable = models.BooleanField(default=True)

    # Room Features
    room_size_sqft = models.PositiveIntegerField(null=True, blank=True, help_text="Room area in sq ft")
    features = models.TextField(
        blank=True,
        default="",
        help_text="Comma-separated features, e.g. 'Air Conditioning,Bathtub,City View,Free WiFi,Mini-bar'",
    )

    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["base_price_per_night"]

    def __str__(self):
        return f"{self.hotel.name} - {self.name} (₹{self.base_price_per_night}/night)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.hotel.update_starting_price()

    def delete(self, *args, **kwargs):
        hotel = self.hotel
        res = super().delete(*args, **kwargs)
        if hotel:
            hotel.update_starting_price()
        return res


class HotelImage(SoftDeleteModel):
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="images")
    room_type = models.ForeignKey(
        HotelRoomType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="images",
        help_text="Optional: Associate image with a specific room type",
    )
    image = models.ImageField(upload_to=hotel_image_upload_path, max_length=500, validators=[validate_image_size])
    alt_text = models.CharField(max_length=255, blank=True, default="Hotel photo")
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    provider = models.CharField(
        max_length=20,
        choices=[("imagekit", "ImageKit"), ("cloudinary", "Cloudinary")],
        default="imagekit",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-is_primary", "-created_at"]

    def save(self, *args, **kwargs):
        # Use the same ImageUploadService as HostelImage for fast cloud uploads
        from hostels.services import ImageUploadService
        from cms.models import StorageSettings
        from django.utils.text import slugify

        delete_old_image_files(self, ["image"])

        # Set provider from admin-configured active provider
        self.provider = StorageSettings.get_active_provider()

        field_file = self.image
        # Only process new file uploads, not existing URLs
        if field_file and hasattr(field_file, "file") and not str(field_file).startswith("http"):
            try:
                service = ImageUploadService()
                hotel_obj = getattr(self, "hotel", None)
                if not hotel_obj and getattr(self, "hotel_id", None):
                    hotel_obj = Hotel.objects.filter(id=self.hotel_id).first()

                if hotel_obj and getattr(hotel_obj, "slug", None):
                    hotel_slug = hotel_obj.slug
                elif hotel_obj and getattr(hotel_obj, "name", None):
                    hotel_slug = slugify(hotel_obj.name)
                else:
                    hotel_slug = f"hotel-{getattr(self, 'hotel_id', 'unknown')}"

                folder = f"hotels/{hotel_slug}"
                orig_name = getattr(field_file, "name", "image")
                ext = os.path.splitext(orig_name)[1] or ".webp"
                order_num = getattr(self, "order", 0) or 0
                meaningful_name = f"{hotel_slug}-photo-{order_num + 1}{ext}"
                result = service.upload_image(field_file, meaningful_name, folder=folder)
                self.image = result["url"]
                self.provider = result["provider"]
            except Exception as e:
                print(f"DEBUG: HotelImage upload failed: {e}")
                process_image_fields(self, ["image"])

        super().save(*args, **kwargs)

    def delete_file_from_storage(self):
        """Hard delete image file from ImageKit / Cloudinary storage."""
        if self.image:
            image_val = str(self.image)
            try:
                from Hbackend.imagekit_storage import ImageKitStorage
                from Hbackend.cloudinary_storage import CloudinaryStorage
                if self.provider == "cloudinary" or "res.cloudinary.com" in image_val:
                    CloudinaryStorage().delete(image_val)
                else:
                    ImageKitStorage().delete(image_val)
            except Exception as e:
                print(f"DEBUG: Failed to delete hotel image from storage: {e}")

    def delete(self, *args, **kwargs):
        self.delete_file_from_storage()
        # Permanently hard delete record
        super().hard_delete(*args, **kwargs)

    def hard_delete(self, *args, **kwargs):
        self.delete_file_from_storage()
        super().hard_delete(*args, **kwargs)

    def __str__(self):
        return f"{self.hotel.name} Image #{self.order}"



# ─────────────────────────────────────────────────────────────────────────────
# MODULAR BOOKING ARCHITECTURE FOR HOTELS
# ─────────────────────────────────────────────────────────────────────────────

class HotelBooking(SoftDeleteModel):
    """
    Core hotel reservation entity keeping essential timeline, inventory, and status.
    Guest information, payments, and cancellations are cleanly decoupled into dedicated models.
    """
    class BookingStatus(models.TextChoices):
        PENDING = "pending", "Pending Confirmation"
        PAYMENT_INITIATED = "payment_initiated", "Payment Initiated"
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_IN = "checked_in", "Checked In"
        CHECKED_OUT = "checked_out", "Checked Out"
        CANCELLED = "cancelled", "Cancelled"
        NO_SHOW = "no_show", "No Show"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_reference = models.CharField(max_length=30, unique=True, editable=False, db_index=True)

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hotel_bookings",
        help_text="Registered user who made the reservation (if authenticated)",
    )
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="bookings")
    owner = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="hotel_owner_bookings",
        null=True,
        blank=True,
        help_text="Hotel Owner receiving the booking",
    )
    room_type = models.ForeignKey(HotelRoomType, on_delete=models.CASCADE, related_name="bookings")

    # Dates & Counts
    check_in_date = models.DateField(db_index=True)
    check_out_date = models.DateField(db_index=True)
    number_of_nights = models.PositiveIntegerField(default=1)
    number_of_rooms = models.PositiveIntegerField(default=1)

    # Grand Total
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Grand total payable for the stay")

    # Status
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.CONFIRMED,
        db_index=True,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Expiry deadline for completing payment/confirmation (25 mins initial, +20 mins on payment initiation)",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.booking_reference} - {self.hotel.name} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            random_suffix = secrets.token_hex(3).upper()
            self.booking_reference = f"HTL-{random_suffix}"
            while HotelBooking.all_objects.filter(booking_reference=self.booking_reference).exists():
                random_suffix = secrets.token_hex(3).upper()
                self.booking_reference = f"HTL-{random_suffix}"

        if self.hotel and not self.owner_id:
            self.owner = getattr(self.hotel, 'owner', None)

        if not self.expires_at and self.status in [
            HotelBooking.BookingStatus.PENDING,
            HotelBooking.BookingStatus.PAYMENT_INITIATED,
        ]:
            from django.utils import timezone
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(minutes=25)

        if self.check_in_date and self.check_out_date:
            delta = (self.check_out_date - self.check_in_date).days
            self.number_of_nights = max(delta, 1)

        super().save(*args, **kwargs)


class HotelGuest(SoftDeleteModel):
    """
    Dedicated model for guest details, headcounts, and special requests.
    """
    booking = models.OneToOneField(
        HotelBooking,
        on_delete=models.CASCADE,
        related_name="guest_details",
        primary_key=True,
    )
    guest_name = models.CharField(max_length=255, help_text="Primary guest full name")
    guest_email = models.EmailField()
    mobile_number = models.CharField(max_length=20)
    adults_count = models.PositiveIntegerField(default=1)
    children_count = models.PositiveIntegerField(default=0)
    special_requests = models.TextField(blank=True, null=True, help_text="Arrival time, preferences, dietary requests")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.guest_name} ({self.mobile_number}) for {self.booking.booking_reference}"


class HotelPayment(SoftDeleteModel):
    """
    Dedicated model for hotel billing breakdown, payment gateway tracking, and transaction history.
    """
    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"
        REFUNDED = "refunded", "Refunded"
        FAILED = "failed", "Failed"

    class PaymentMethod(models.TextChoices):
        ONLINE = "online", "Online Payment"
        PAY_AT_HOTEL = "pay_at_hotel", "Pay at Hotel"
        ON_ARRIVAL = "on_arrival", "Pay on Arrival"

    booking = models.OneToOneField(
        HotelBooking,
        on_delete=models.CASCADE,
        related_name="payment_details",
        primary_key=True,
    )
    room_rate_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="rooms * nights * rate")
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.ONLINE,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    transaction_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Gateway transaction or reference ID",
    )
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for {self.booking.booking_reference}: ₹{self.total_amount} ({self.get_payment_status_display()})"


class HotelCancellation(SoftDeleteModel):
    """
    Dedicated audit model for hotel cancellation records and refund processing.
    """
    class CancelledBy(models.TextChoices):
        GUEST = "guest", "Guest"
        HOTEL_ADMIN = "hotel_admin", "Hotel / Admin"
        SYSTEM = "system", "System Auto-Cancelled"

    class RefundStatus(models.TextChoices):
        PENDING = "pending", "Refund Pending"
        PROCESSED = "processed", "Refund Processed"
        NON_REFUNDABLE = "non_refundable", "Non-Refundable"

    booking = models.OneToOneField(
        HotelBooking,
        on_delete=models.CASCADE,
        related_name="cancellation_details",
        primary_key=True,
    )
    cancelled_by = models.CharField(
        max_length=20,
        choices=CancelledBy.choices,
        default=CancelledBy.GUEST,
    )
    reason = models.TextField(blank=True, null=True, help_text="Reason for cancellation")
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    refund_status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
    )
    cancelled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cancellation for {self.booking.booking_reference} (Refund: ₹{self.refund_amount})"
