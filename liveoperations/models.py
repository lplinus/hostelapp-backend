from django.conf import settings
from django.db import models
from Hbackend.base_models import SoftDeleteModel


class HousekeepingTask(SoftDeleteModel):
    class Stream(models.TextChoices):
        HOTEL = "hotel", "Hotel"
        VACATION_RENTAL = "vacation_rental", "Vacation Rental"

    class Status(models.TextChoices):
        CLEAN = "clean", "Clean"
        DIRTY = "dirty", "Dirty"
        IN_PROGRESS = "in_progress", "In Progress"
        INSPECTION_NEEDED = "inspection_needed", "Inspection Needed"
        READY = "ready", "Ready for Guest"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        HIGH = "high", "High (Urgent Arrival)"
        LOW = "low", "Low"

    stream = models.CharField(max_length=20, choices=Stream.choices, default=Stream.HOTEL)
    hotel = models.ForeignKey(
        "hotels.Hotel",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="housekeeping_tasks",
    )
    vacation_rental = models.ForeignKey(
        "vacanationrentals.VacationRental",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="housekeeping_tasks",
    )
    unit_identifier = models.CharField(
        max_length=120,
        help_text="Room number (e.g. 101) or specific villa unit title",
    )
    floor = models.CharField(max_length=50, blank=True, default="")
    status = models.CharField(
        max_length=25,
        choices=Status.choices,
        default=Status.DIRTY,
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    linen_changed = models.BooleanField(default=False)
    restocked = models.BooleanField(default=False)
    inspected = models.BooleanField(default=False)
    assigned_staff = models.CharField(max_length=120, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    next_check_in = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "unit_identifier"]
        verbose_name = "Housekeeping Task"
        verbose_name_plural = "Housekeeping Tasks"

    def __str__(self):
        return f"{self.unit_identifier} ({self.get_status_display()})"


class PropertyDateBlock(SoftDeleteModel):
    class Stream(models.TextChoices):
        HOTEL = "hotel", "Hotel"
        VACATION_RENTAL = "vacation_rental", "Vacation Rental"

    class Reason(models.TextChoices):
        MAINTENANCE = "maintenance", "Maintenance / Repair"
        OWNER_STAY = "owner_stay", "Owner Personal Stay"
        BLACKOUT = "blackout", "Blackout / Blocked"
        SEASONAL_CLOSURE = "seasonal_closure", "Seasonal Closure"

    stream = models.CharField(max_length=20, choices=Stream.choices, default=Stream.HOTEL)
    hotel = models.ForeignKey(
        "hotels.Hotel",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="date_blocks",
    )
    vacation_rental = models.ForeignKey(
        "vacanationrentals.VacationRental",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="date_blocks",
    )
    unit_identifier = models.CharField(
        max_length=120,
        help_text="Room number or vacation rental title",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(
        max_length=50,
        choices=Reason.choices,
        default=Reason.MAINTENANCE,
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_date"]
        verbose_name = "Property Date Block"
        verbose_name_plural = "Property Date Blocks"

    def __str__(self):
        return f"{self.unit_identifier}: {self.start_date} to {self.end_date} ({self.get_reason_display()})"


class DigitalGuestAccess(SoftDeleteModel):
    class Stream(models.TextChoices):
        HOTEL = "hotel", "Hotel"
        VACATION_RENTAL = "vacation_rental", "Vacation Rental"

    class KycStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    stream = models.CharField(max_length=20, choices=Stream.choices, default=Stream.HOTEL)
    hotel_booking = models.ForeignKey(
        "hotels.HotelBooking",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="guest_access",
    )
    vacation_booking = models.ForeignKey(
        "vacanationrentals.VacationRentalBooking",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="guest_access",
    )
    access_code = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Smart lock PIN code or keybox lock combination",
    )
    wifi_ssid = models.CharField(max_length=100, blank=True, default="")
    wifi_password = models.CharField(max_length=100, blank=True, default="")
    instructions_sent = models.BooleanField(default=False)
    instructions_sent_at = models.DateTimeField(null=True, blank=True)
    kyc_status = models.CharField(
        max_length=20,
        choices=KycStatus.choices,
        default=KycStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Digital Guest Access"
        verbose_name_plural = "Digital Guest Access"

    def __str__(self):
        return f"Access for {self.hotel_booking or self.vacation_booking} (Code: {self.access_code})"


class SecurityDepositLedger(SoftDeleteModel):
    class Status(models.TextChoices):
        HELD = "held", "Held / Authorized"
        RELEASED = "released", "Released back to Guest"
        DEDUCTED = "deducted", "Deducted for Damages"

    vacation_booking = models.OneToOneField(
        "vacanationrentals.VacationRentalBooking",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="deposit_ledger",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.HELD,
    )
    deduction_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    deduction_reason = models.TextField(blank=True, default="")
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Security Deposit Ledger"
        verbose_name_plural = "Security Deposit Ledgers"

    def __str__(self):
        return f"Deposit {self.amount} for {self.vacation_booking} ({self.get_status_display()})"


class LiveMealPlan(SoftDeleteModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="live_meal_plans",
    )
    hotel = models.ForeignKey(
        "hotels.Hotel",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="live_meal_plans",
    )
    code = models.CharField(max_length=16)
    name = models.CharField(max_length=120)
    surcharge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    desc = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Live Meal Plan"
        verbose_name_plural = "Live Meal Plans"

    def __str__(self):
        return f"{self.code} - {self.name}"


class LiveSeasonalMultiplier(SoftDeleteModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="live_seasonal_multipliers",
    )
    hotel = models.ForeignKey(
        "hotels.Hotel",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="live_seasonal_multipliers",
    )
    name = models.CharField(max_length=120)
    multiplier = models.CharField(max_length=32)
    dates = models.CharField(max_length=120, blank=True, default="")
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Live Seasonal Multiplier"
        verbose_name_plural = "Live Seasonal Multipliers"

    def __str__(self):
        return f"{self.name} ({self.multiplier})"


class LiveMinStayRule(SoftDeleteModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="live_min_stay_rules",
    )
    hotel = models.ForeignKey(
        "hotels.Hotel",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="live_min_stay_rules",
    )
    standard_min_nights = models.PositiveIntegerField(default=1)
    weekend_min_nights = models.PositiveIntegerField(default=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Live Min Stay Rule"
        verbose_name_plural = "Live Min Stay Rules"

    def __str__(self):
        return f"MinLOS {self.standard_min_nights} / Weekend {self.weekend_min_nights}"


class LivePromoCoupon(SoftDeleteModel):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="live_promo_coupons",
    )
    hotel = models.ForeignKey(
        "hotels.Hotel",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="live_promo_coupons",
    )
    code = models.CharField(max_length=40)
    discount = models.CharField(max_length=60)
    min_nights = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Live Promo Coupon"
        verbose_name_plural = "Live Promo Coupons"

    def __str__(self):
        return f"{self.code} ({self.discount})"
