from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from Hbackend.base_models import SoftDeleteModel
from Hbackend.bunny_storage import bunny_storage


def ad_banner_upload_path(instance, filename):
    import os
    ext = os.path.splitext(filename)[1].lower() or ".webp"
    return f"ads/banners/campaign_{instance.id or 'temp'}_{timezone.now().strftime('%Y%m%d%H%M%S')}{ext}"


class AdCampaign(SoftDeleteModel):
    class AdType(models.TextChoices):
        SPONSORED_LISTING = "sponsored_listing", "Sponsored Listing Boost"
        DISPLAY_BANNER = "display_banner", "Display Banner Ad"

    class PlacementSlot(models.TextChoices):
        SEARCH_FEED_TOP = "search_feed_top", "Search Feed Top (Rank #1 & #2)"
        LISTING_SIDEBAR = "listing_sidebar", "Listing Detail Sidebar Spotlight"
        CITY_HEADER = "city_header", "Destination City Header Showcase"

    class PropertyType(models.TextChoices):
        HOTEL = "hotel", "Hotel"
        VACATION_RENTAL = "vacation_rental", "Vacation Rental"
        HOSTEL = "hostel", "Hostel"

    class CampaignStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        PENDING = "pending", "Pending Payment"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ad_campaigns",
        help_text="Property owner who created the campaign",
    )

    campaign_name = models.CharField(max_length=255, help_text="Descriptive campaign title")
    ad_type = models.CharField(
        max_length=30,
        choices=AdType.choices,
        default=AdType.SPONSORED_LISTING,
        db_index=True,
    )
    placement = models.CharField(
        max_length=30,
        choices=PlacementSlot.choices,
        default=PlacementSlot.SEARCH_FEED_TOP,
        db_index=True,
    )
    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.choices,
        default=PropertyType.VACATION_RENTAL,
        db_index=True,
    )

    # Linked Properties (Focus on Vacation Rentals & Hotels)
    hotel = models.ForeignKey(
        "hotels.Hotel",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="ad_campaigns",
        help_text="Target Hotel if property_type is Hotel",
    )
    vacation_rental = models.ForeignKey(
        "vacanationrentals.VacationRental",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="ad_campaigns",
        help_text="Target Vacation Rental if property_type is Vacation Rental",
    )
    hostel = models.ForeignKey(
        "hostels.Hostel",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ad_campaigns",
        help_text="Target Hostel (optional)",
    )

    # Custom banner image if ad_type is display_banner
    banner_image = models.ImageField(
        upload_to=ad_banner_upload_path,
        storage=bunny_storage,
        null=True,
        blank=True,
        help_text="Custom graphical banner stored on Bunny CDN",
    )
    destination_url = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Custom landing destination link",
    )

    # Duration & Budget
    duration_days = models.PositiveIntegerField(default=15, help_text="Campaign duration in days")
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Total promotion budget in INR")

    # Dates
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(blank=True, null=True)

    # Status & Counters
    status = models.CharField(
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.ACTIVE,
        db_index=True,
    )
    impressions_count = models.PositiveIntegerField(default=0, help_text="Total guest impressions served")
    clicks_count = models.PositiveIntegerField(default=0, help_text="Total guest clicks received")
    max_impressions = models.PositiveIntegerField(default=0, help_text="Maximum allowed impressions budget cap (0 = unlimited)")
    max_clicks = models.PositiveIntegerField(default=0, help_text="Maximum allowed clicks budget cap (0 = unlimited)")
    weight = models.PositiveIntegerField(default=1, help_text="Serving weight for weighted random selection (higher weight = served more often)")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Ad Campaign"
        verbose_name_plural = "Ad Campaigns"

    def __str__(self):
        return f"{self.campaign_name} ({self.get_property_type_display()} - {self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Automatically compute end_date if missing
        if self.start_date and not self.end_date and self.duration_days:
            self.end_date = self.start_date + timedelta(days=self.duration_days)
        super().save(*args, **kwargs)

    @property
    def is_active_serving(self):
        now = timezone.now()
        if self.is_deleted != 0:
            return False
        if self.status != self.CampaignStatus.ACTIVE:
            return False
        if self.start_date and self.start_date > now:
            return False
        if self.end_date and self.end_date < now:
            return False
        # Budget stop: max_impressions / max_clicks
        if self.max_impressions > 0 and self.impressions_count >= self.max_impressions:
            return False
        if self.max_clicks > 0 and self.clicks_count >= self.max_clicks:
            return False
        return True

    @property
    def ctr(self):
        """Click-through rate percentage."""
        if self.impressions_count > 0:
            return round((self.clicks_count / self.impressions_count) * 100, 2)
        return 0.0

    @property
    def days_remaining(self):
        if not self.end_date:
            return 0
        diff = (self.end_date - timezone.now()).total_seconds()
        if diff <= 0:
            return 0
        return int(diff // 86400) + 1

    @property
    def target_property_title(self):
        if self.vacation_rental:
            return getattr(self.vacation_rental, "title", "Vacation Rental")
        if self.hotel:
            return getattr(self.hotel, "name", "Hotel")
        if self.hostel:
            return getattr(self.hostel, "name", "Hostel")
        return "Unlinked Property"

    @property
    def target_property_city(self):
        if self.vacation_rental and getattr(self.vacation_rental, "city", None):
            return getattr(self.vacation_rental.city, "name", "")
        if self.hotel and getattr(self.hotel, "city", None):
            return getattr(self.hotel.city, "name", "")
        if self.hostel and getattr(self.hostel, "city", None):
            return getattr(self.hostel.city, "name", "")
        return ""

    @property
    def target_property_price(self):
        if self.vacation_rental:
            return float(getattr(self.vacation_rental, "price_per_night", 0) or 0)
        if self.hotel:
            return float(getattr(self.hotel, "starting_price_per_night", 0) or 0)
        if self.hostel:
            return float(getattr(self.hostel, "price", 0) or 0)
        return 0.0

    @property
    def target_property_rating(self):
        if self.vacation_rental:
            return float(getattr(self.vacation_rental, "rating_avg", 5.0) or 5.0)
        if self.hotel:
            return float(getattr(self.hotel, "rating_avg", 5.0) or 5.0)
        if self.hostel:
            return float(getattr(self.hostel, "rating_avg", 5.0) or 5.0)
        return 5.0

    @property
    def target_property_slug(self):
        if self.vacation_rental:
            return getattr(self.vacation_rental, "slug", str(self.vacation_rental.id))
        if self.hotel:
            return getattr(self.hotel, "slug", str(self.hotel.id))
        if self.hostel:
            return getattr(self.hostel, "slug", str(self.hostel.id))
        return ""

    @property
    def target_property_address(self):
        if self.vacation_rental:
            return getattr(self.vacation_rental, "address", "")
        if self.hotel:
            return getattr(self.hotel, "address", "")
        if self.hostel:
            return getattr(self.hostel, "address", "")
        return ""


class AdPlan(SoftDeleteModel):
    """
    Backend-configured pricing and duration plans for AdSense & Sponsored Promotions.
    """
    plan_code = models.CharField(max_length=50, unique=True, help_text="Unique package id e.g. pkg-7, pkg-15")
    name = models.CharField(max_length=100, help_text="Plan display name e.g. Growth Spotlight")
    duration_days = models.PositiveIntegerField(help_text="Duration in days")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Package price in INR")
    description = models.TextField(blank=True, default="", help_text="Marketing description")
    is_popular = models.BooleanField(default=False, help_text="Flag as most popular / recommended")
    is_active = models.BooleanField(default=True, help_text="Active for purchase")
    order = models.PositiveIntegerField(default=0, help_text="Display ordering")

    class Meta:
        ordering = ["order", "duration_days"]

    def __str__(self):
        return f"{self.name} - {self.duration_days} Days (₹{self.price})"

    @property
    def duration_display(self):
        return f"{self.duration_days} Days"

