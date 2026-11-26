#from django.contrib.gis.db import models as gis_models  # Alias to avoid collision with standard django.db.models
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
    property_type = models.CharField(max_length=30, choices=PROPERTY_TYPES, default="hotel")
    property_id = models.CharField(max_length=36, null=True, blank=True, db_index=True)
    title = models.CharField(max_length=255)

    # Exact coordinates
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)

    # Native PostGIS Point Field for high-performance spatial queries (Longitude, Latitude)
    # location = gis_models.PointField(srid=4326, geography=True, null=True, blank=True)

    # Address & location info
    formatted_address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True, help_text="Prominent nearby landmark")
    directions_guide = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed offline directions guide"
    )

    # Auto-fetch flags
    is_auto_fetched = models.BooleanField(default=False)
    gps_accuracy = models.FloatField(null=True, blank=True)

    # Offline map payload
    offline_map_data = models.JSONField(default=dict, blank=True)
    offline_tile_bounds = models.JSONField(default=dict, blank=True)

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








###any map places

        # maps/models.py
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator, MaxValueValidator


class MapPlace(models.Model):
    CATEGORY_CHOICES = [
        ("hotel", "Hotel"),
        ("rental", "Vacation Rental"),
        ("shop", "Shop"),
        ("food", "Food & Cafe"),
        ("vendor", "Vendor"),
        ("service", "Service"),
        ("attraction", "Famous Place"),
        ("viewpoint", "Viewpoint"),
        ("transport", "Transport"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="other", db_index=True)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=9, decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)])
    landmark = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=300, blank=True)
    city = models.CharField(max_length=100, blank=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    image = models.ImageField(upload_to="map_places/", blank=True, null=True)
    link_url = models.CharField(max_length=300, blank=True)  # e.g. /hotels/lake-pichola-grand

    # Optional link to any other model (Hotel, Vendor, Shop...) without needing a new table each time
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    linked_object = GenericForeignKey("content_type", "object_id")

    is_active = models.BooleanField(default=True)   # hide a pin without deleting it
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["latitude", "longitude"])]

    def __str__(self):
        return f"{self.title} ({self.category})"