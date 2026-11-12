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


class VacationRental(SoftDeleteModel):
    class RentalType(models.TextChoices):
        ENTIRE_PLACE = "entire_place", "Entire Place"
        PRIVATE_ROOM = "private_room", "Private Room"
        SHARED_ROOM = "shared_room", "Shared Room"

    class PropertyCategory(models.TextChoices):
        VILLA = "villa", "Villa"
        APARTMENT = "apartment", "Apartment"
        HOUSE = "house", "Independent House"
        COTTAGE = "cottage", "Cottage"
        FARMHOUSE = "farmhouse", "Farmhouse"
        BEACH_HOUSE = "beach_house", "Beach House"
        CABIN = "cabin", "Cabin"
        PENTHOUSE = "penthouse", "Penthouse"
        STUDIO = "studio", "Studio"

    class CancellationPolicy(models.TextChoices):
        FLEXIBLE = "flexible", "Flexible (Full refund up to 1 day prior)"
        MODERATE = "moderate", "Moderate (Full refund up to 5 days prior)"
        STRICT = "strict", "Strict (50% refund up to 7 days prior)"
        NON_REFUNDABLE = "non_refundable", "Non-Refundable"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    host = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="vacation_rentals",
        help_text="Host / Property Owner",
    )

    # Basic Info
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    tagline = models.CharField(max_length=255, blank=True, null=True, help_text="e.g. Luxurious 3BHK Villa with Private Pool")
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True, null=True)

    rental_type = models.CharField(
        max_length=30,
        choices=RentalType.choices,
        default=RentalType.ENTIRE_PLACE,
        db_index=True,
    )
    category = models.CharField(
        max_length=30,
        choices=PropertyCategory.choices,
        default=PropertyCategory.VILLA,
        db_index=True,
    )

    # Location
    city = models.ForeignKey("locations.City", on_delete=models.CASCADE, related_name="vacation_rentals")
    area = models.ForeignKey("locations.Area", on_delete=models.SET_NULL, null=True, blank=True, related_name="vacation_rentals")
    address = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Space & Capacity (Airbnb Specs)
    max_guests = models.PositiveIntegerField(default=4)
    bedrooms = models.PositiveIntegerField(default=2)
    beds = models.PositiveIntegerField(default=2)
    bathrooms = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=Decimal("2.0"),
        help_text="Number of bathrooms (e.g. 1.5, 2.0)",
    )

    # Pricing & Fees
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, help_text="Base nightly price")
    weekend_price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Optional surge pricing for Friday & Saturday",
    )
    cleaning_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="One-time cleaning fee per stay",
    )
    security_deposit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Refundable damage/security deposit",
    )

    # Discounts
    weekly_discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Discount for stays of 7+ nights",
    )
    monthly_discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Discount for stays of 28+ nights",
    )

    # Booking Rules & Check-in
    min_nights = models.PositiveIntegerField(default=1)
    max_nights = models.PositiveIntegerField(default=30)
    check_in_time = models.TimeField(default="15:00")
    check_out_time = models.TimeField(default="11:00")
    instant_book = models.BooleanField(
        default=True,
        help_text="True if guests can book instantly without host prior approval",
    )
    cancellation_policy = models.CharField(
        max_length=30,
        choices=CancellationPolicy.choices,
        default=CancellationPolicy.FLEXIBLE,
    )

    # House Rules
    allows_pets = models.BooleanField(default=False)
    allows_smoking = models.BooleanField(default=False)
    allows_parties = models.BooleanField(default=False)
    custom_rules = models.TextField(blank=True, null=True, help_text="Additional host house rules")

    # Caretaker & On-Site Host Contact
    caretaker_name = models.CharField(max_length=150, blank=True, null=True, help_text="On-site caretaker / property manager name")
    caretaker_number = models.CharField(max_length=20, blank=True, null=True, help_text="Caretaker contact phone / mobile number")

    # Wi-Fi & Internet Credentials
    wifi_name = models.CharField(max_length=100, blank=True, null=True, help_text="Wi-Fi network name / SSID")
    wifi_password = models.CharField(max_length=100, blank=True, null=True, help_text="Wi-Fi password for guests")

    # Amenities
    amenities = models.ManyToManyField("amenities.Amenity", related_name="vacation_rentals", blank=True)

    # Quality & Rating metrics
    rating_avg = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)
    is_superhost = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)

    # SEO & Media
    og_image = models.ImageField(
        upload_to="seo/vacation_rentals/",
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
        return f"{self.title} ({self.get_category_display()} in {self.city.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while VacationRental.all_objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        delete_old_image_files(self, ["og_image"])
        process_image_fields(self, ["og_image"])
        super().save(*args, **kwargs)


class VacationRentalImage(SoftDeleteModel):
    rental = models.ForeignKey(VacationRental, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="vacation_rentals/", max_length=500, validators=[validate_image_size])
    caption = models.CharField(max_length=255, blank=True, null=True, help_text="e.g. Master Bedroom, Infinity Pool")
    is_primary = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-is_primary", "-created_at"]

    def save(self, *args, **kwargs):
        delete_old_image_files(self, ["image"])
        process_image_fields(self, ["image"])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.rental.title} Photo #{self.order}"


class VacationRentalAvailability(models.Model):
    class BlockReason(models.TextChoices):
        BOOKED = "booked", "Booked by Guest"
        MAINTENANCE = "maintenance", "Maintenance"
        HOST_RESERVED = "host_reserved", "Blocked by Host"

    rental = models.ForeignKey(
        VacationRental,
        on_delete=models.CASCADE,
        related_name="availability_records",
    )
    date = models.DateField(db_index=True)
    is_available = models.BooleanField(default=True)
    custom_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Custom price override for this specific date (e.g. holiday surge)",
    )
    reason = models.CharField(
        max_length=30,
        choices=BlockReason.choices,
        default=BlockReason.HOST_RESERVED,
    )

    class Meta:
        unique_together = ("rental", "date")
        indexes = [models.Index(fields=["rental", "date"])]

    def __str__(self):
        status = "Available" if self.is_available else f"Blocked ({self.get_reason_display()})"
        return f"{self.rental.title} | {self.date} | {status}"


# ─────────────────────────────────────────────────────────────────────────────
# MODULAR BOOKING ARCHITECTURE FOR VACATION RENTALS (AIRBNB STYLE)
# ─────────────────────────────────────────────────────────────────────────────

class VacationRentalBooking(SoftDeleteModel):
    """
    Core vacation rental reservation entity.
    Headcount breakdown, itemized Airbnb pricing, and cancellations are cleanly decoupled into dedicated models.
    """
    class BookingStatus(models.TextChoices):
        PENDING_APPROVAL = "pending_approval", "Pending Host Approval"
        PAYMENT_INITIATED = "payment_initiated", "Payment Initiated"
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_IN = "checked_in", "Checked In"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        DECLINED = "declined", "Declined by Host"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_reference = models.CharField(max_length=30, unique=True, editable=False, db_index=True)

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vacation_rental_bookings",
        help_text="Guest who booked",
    )
    rental = models.ForeignKey(
        VacationRental,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    host = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="hosted_rental_bookings",
        help_text="Host receiving the booking",
    )
    owner = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="vacation_rental_owner_bookings",
        null=True,
        blank=True,
        help_text="Owner / Host receiving the booking",
    )

    # Dates & Nights
    check_in_date = models.DateField(db_index=True)
    check_out_date = models.DateField(db_index=True)
    number_of_nights = models.PositiveIntegerField(default=1)

    # Grand Total
    total_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Final payable amount")

    # Status
    status = models.CharField(
        max_length=25,
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
        return f"{self.booking_reference} - {self.rental.title} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            random_suffix = secrets.token_hex(3).upper()
            self.booking_reference = f"VRB-{random_suffix}"
            while VacationRentalBooking.all_objects.filter(booking_reference=self.booking_reference).exists():
                random_suffix = secrets.token_hex(3).upper()
                self.booking_reference = f"VRB-{random_suffix}"

        if self.rental:
            if not self.host_id:
                self.host = self.rental.host
            if not self.owner_id:
                self.owner = self.rental.host or self.host
        elif self.host and not self.owner_id:
            self.owner = self.host

        if self.check_in_date and self.check_out_date:
            delta = (self.check_out_date - self.check_in_date).days
            self.number_of_nights = max(delta, 1)

        # If property requires host approval, set to PENDING_APPROVAL on create
        if not self.pk and self.rental and not self.rental.instant_book:
            if self.status == VacationRentalBooking.BookingStatus.CONFIRMED:
                self.status = VacationRentalBooking.BookingStatus.PENDING_APPROVAL

        if not self.expires_at and self.status in [
            VacationRentalBooking.BookingStatus.PENDING_APPROVAL,
            VacationRentalBooking.BookingStatus.PAYMENT_INITIATED,
        ]:
            from django.utils import timezone
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(minutes=25)

        super().save(*args, **kwargs)


class VacationRentalGuest(SoftDeleteModel):
    """
    Dedicated model for vacation rental guest details and Airbnb-style headcount breakdown.
    """
    booking = models.OneToOneField(
        VacationRentalBooking,
        on_delete=models.CASCADE,
        related_name="guest_details",
        primary_key=True,
    )
    guest_name = models.CharField(max_length=255, help_text="Primary guest full name")
    guest_email = models.EmailField()
    mobile_number = models.CharField(max_length=20)

    # Multi-tier headcount (Airbnb standard)
    adults = models.PositiveIntegerField(default=1)
    children = models.PositiveIntegerField(default=0)
    infants = models.PositiveIntegerField(default=0)
    pets = models.PositiveIntegerField(default=0)
    total_guests = models.PositiveIntegerField(default=1)

    special_requests = models.TextField(blank=True, null=True, help_text="Notes to the host")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.total_guests = self.adults + self.children
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.guest_name} ({self.total_guests} guests) for {self.booking.booking_reference}"


class VacationRentalPayment(SoftDeleteModel):
    """
    Dedicated model for itemized Airbnb pricing breakdown and payment status.
    """
    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        PARTIALLY_PAID = "partially_paid", "Partially Paid"
        REFUNDED = "refunded", "Refunded"
        FAILED = "failed", "Failed"

    class PaymentMethod(models.TextChoices):
        ONLINE = "online", "Online Payment"
        ON_ARRIVAL = "on_arrival", "Pay on Arrival"

    booking = models.OneToOneField(
        VacationRentalBooking,
        on_delete=models.CASCADE,
        related_name="pricing_details",
        primary_key=True,
    )
    nightly_rate_applied = models.DecimalField(max_digits=10, decimal_places=2)
    stay_subtotal = models.DecimalField(max_digits=10, decimal_places=2, help_text="nights * rate")
    cleaning_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    service_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), help_text="Platform fee")
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"), help_text="Weekly/monthly discount")
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

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
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for {self.booking.booking_reference}: ₹{self.total_price} ({self.get_payment_status_display()})"


class VacationRentalCancellation(SoftDeleteModel):
    """
    Dedicated audit model for vacation rental cancellation and refund tracking.
    """
    class CancelledBy(models.TextChoices):
        GUEST = "guest", "Guest"
        HOST = "host", "Host"
        ADMIN = "admin", "Admin"

    class RefundStatus(models.TextChoices):
        PENDING = "pending", "Refund Pending"
        PROCESSED = "processed", "Refund Processed"
        NON_REFUNDABLE = "non_refundable", "Non-Refundable"

    booking = models.OneToOneField(
        VacationRentalBooking,
        on_delete=models.CASCADE,
        related_name="cancellation_details",
        primary_key=True,
    )
    cancellation_policy_applied = models.CharField(max_length=30, blank=True, null=True)
    cancelled_by = models.CharField(
        max_length=20,
        choices=CancelledBy.choices,
        default=CancelledBy.GUEST,
    )
    reason = models.TextField(blank=True, null=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    refund_status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
    )
    cancelled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cancellation for {self.booking.booking_reference} (Refund: ₹{self.refund_amount})"
