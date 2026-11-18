from django.db import models
from django.conf import settings
from Hbackend.base_models import SoftDeleteModel


class PropertyPinpoint(SoftDeleteModel):
    PROPERTY_TYPES = (
        ("hostel", "Hostel"),
        ("hotel", "Hotel"),
        ("vacation_rental", "Vacation Rental"),
        ("custom", "Custom Location"),
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="property_pinpoints",
        null=True,
        blank=True
    )
    property_type = models.CharField(max_length=30, choices=PROPERTY_TYPES, default="hostel")
    property_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    title = models.CharField(max_length=255)

    # Exact coordinates
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)

    # Address & location info
    formatted_address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True, help_text="Prominent nearby landmark")
    directions_guide = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed offline directions guide (e.g., turn left after gate, 2nd building on right)"
    )

    # Auto-fetch flags
    is_auto_fetched = models.BooleanField(
        default=False,
        help_text="Whether this pinpoint was auto-fetched using GPS / device geolocation"
    )
    gps_accuracy = models.FloatField(
        null=True,
        blank=True,
        help_text="Reported GPS accuracy radius in meters"
    )

    # Offline map payload
    offline_map_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="GeoJSON and offline tile caching specs"
    )
    offline_tile_bounds = models.JSONField(
        default=dict,
        blank=True,
        help_text="Pre-calculated bounds [southWest, northEast] for offline downloading"
    )

    is_verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["property_type", "property_id"]),
            models.Index(fields=["latitude", "longitude"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.property_type} #{self.property_id or 'N/A'}) - [{self.latitude}, {self.longitude}]"

    def calculate_offline_bounds(self, buffer_deg=0.015):
        lat = float(self.latitude)
        lng = float(self.longitude)
        return {
            "southWest": {"lat": round(lat - buffer_deg, 6), "lng": round(lng - buffer_deg, 6)},
            "northEast": {"lat": round(lat + buffer_deg, 6), "lng": round(lng + buffer_deg, 6)},
            "center": {"lat": lat, "lng": lng},
            "zoom_levels": [14, 15, 16, 17, 18],
        }

    def save(self, *args, **kwargs):
        if not self.offline_tile_bounds and self.latitude and self.longitude:
            self.offline_tile_bounds = self.calculate_offline_bounds()
        super().save(*args, **kwargs)
