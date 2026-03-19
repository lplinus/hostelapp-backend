from django.db import models
from locations.models import City, Area
from accounts.models import User
from Hbackend.utils import process_image_fields, delete_old_image_files
from Hbackend.imagekit_storage import ImageKitStorage   
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from Hbackend.base_models import SoftDeleteModel


class Hostel(SoftDeleteModel):
    name = models.CharField(max_length=255)

    class HostelType(models.TextChoices):
        BOYS = "boys", "Boys Hostel"
        GIRLS = "girls", "Girls Hostel"
        CO_LIVING = "co_living", "Co-Living Hostel"
        WORKING_PROFESSIONAL = "working_professional", "Working Professionals Hostel"
        STUDENT = "student", "Student Hostel"
        LUXURY = "luxury", "Luxury Hostel"
        BUDGET = "budget", "Budget Hostel"
        PG = "pg", "PG Accommodation"

    hostel_type = models.CharField(
        max_length=30,
        choices=HostelType.choices,
        default=HostelType.BOYS,
        db_index=True,
    )
    slug = models.SlugField(unique=True)

    # SEO Fields
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=500, blank=True, null=True)
    canonical_url = models.URLField(blank=True, null=True)
    og_image = models.ImageField(upload_to="seo/hostels/", null=True, blank=True)
    og_title = models.CharField(max_length=255, blank=True, null=True)
    og_description = models.TextField(blank=True, null=True)
    og_type = models.CharField(max_length=50, default="website")
    structured_data = models.JSONField(blank=True, null=True)
    is_indexed = models.BooleanField(default=True)

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hostels")

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="hostels")

    area = models.ForeignKey(
        Area, null=True, blank=True, on_delete=models.CASCADE, related_name="hostels"
    )

    description = models.TextField()
    short_description = models.CharField(max_length=300)

    price = models.DecimalField(null=True, blank=True, max_digits=10, decimal_places=2)
    price_per_day = models.DecimalField(
        null=True, blank=True, max_digits=10, decimal_places=2
    )

    address = models.CharField(max_length=255)
    postal_code = models.CharField(max_length=20, blank=True, null=True)

    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    check_in_time = models.TimeField()
    check_out_time = models.TimeField()

    rating_avg = models.FloatField(default=0)
    rating_count = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_toprated = models.BooleanField(null=True, blank=True, default=False)
    is_verified = models.BooleanField(null=True, blank=True, default=False)
    is_discounted = models.BooleanField(null=True, blank=True, default=False)
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("100")),
        ],
    )
    discounted_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, editable=False
    )
    discounted_price_per_day = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, editable=False
    )
    is_approved = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        delete_old_image_files(self, ["og_image"])
        process_image_fields(self, ["og_image"])

        if self.is_discounted and self.discount_percentage is not None:
            if self.price is not None:
                discount_amount = (self.price * self.discount_percentage) / Decimal(
                    "100"
                )
                self.discounted_price = self.price - discount_amount
            else:
                self.discounted_price = None

            if self.price_per_day is not None:
                discount_amount_day = (
                    self.price_per_day * self.discount_percentage
                ) / Decimal("100")
                self.discounted_price_per_day = self.price_per_day - discount_amount_day
            else:
                self.discounted_price_per_day = None
        else:
            self.discounted_price = None
            self.discounted_price_per_day = None
            self.discount_percentage = None
        super().save(*args, **kwargs)

    @property
    def final_price(self):
        """
        Always use this for booking & API (Monthly).
        """
        if self.is_discounted and self.discounted_price:
            return self.discounted_price
        return self.price

    @property
    def final_price_per_day(self):
        """
        Always use this for booking & API (Daily).
        """
        if self.is_discounted and self.discounted_price_per_day:
            return self.discounted_price_per_day
        return self.price_per_day

    amenities = models.ManyToManyField(
        "amenities.Amenity", related_name="hostels", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["-is_discounted", "-created_at"]


# Hostel images=======================================
class HostelTypeImage(SoftDeleteModel):
    """
    Stores images for each hostel type.
    Managed only via Admin.
    """

    hostel_type = models.CharField(
        max_length=30,
        choices=Hostel.HostelType.choices,
        unique=True,
    )

    image = models.ImageField(upload_to="hostel-type-images/")
    alt_text = models.CharField(
        max_length=255,
        default="Hostel type image",
    )

    def save(self, *args, **kwargs):
        delete_old_image_files(self, ["image"])
        process_image_fields(self, ["image"])
        super().save(*args, **kwargs)

    def __str__(self):
        return dict(Hostel.HostelType.choices).get(self.hostel_type)


class HostelImage(SoftDeleteModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="hostels/")
    image2 = models.ImageField(null=True, blank=True, upload_to="hostels/")
    image3 = models.ImageField(null=True, blank=True, upload_to="hostels/")
    image4 = models.ImageField(null=True, blank=True, upload_to="hostels/")
    image5 = models.ImageField(null=True, blank=True, upload_to="hostels/")
    image6 = models.ImageField(null=True, blank=True, upload_to="hostels/")
    image7 = models.ImageField(null=True, blank=True, upload_to="hostels/")
    image8 = models.ImageField(null=True, blank=True, upload_to="hostels/")
    image9 = models.ImageField(null=True, blank=True, upload_to="hostels/")
    image10 = models.ImageField(null=True, blank=True, upload_to="hostels/")

    alt_text = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        # Delete old files before processing new ones to avoid duplicates
        fields = ["image", "image2", "image3", "image4", "image5", "image6", "image7", "image8", "image9", "image10"]
        delete_old_image_files(self, fields)
        # Convert all image fields to WebP on save
        process_image_fields(self, fields)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.hostel.name} Image"


class DefaultHostelImage(models.Model):
    """
    Singleton model — only one row should exist.
    Stores fallback images shown when a hostel has no images uploaded.
    Upload these via Django Admin → Hostels → Default Hostel Images.
    """

    image1 = models.ImageField(
        upload_to="hostels/defaults/", verbose_name="Default Image 1", null=True, blank=True
    )
    image2 = models.ImageField(
        upload_to="hostels/defaults/",
        verbose_name="Default Image 2",
        null=True,
        blank=True,
    )
    image3 = models.ImageField(
        upload_to="hostels/defaults/",
        verbose_name="Default Image 3",
        null=True,
        blank=True,
    )
    image4 = models.ImageField(
        upload_to="hostels/defaults/",
        verbose_name="Default Image 4",
        null=True,
        blank=True,
    )
    image5 = models.ImageField(
        upload_to="hostels/defaults/",
        verbose_name="Default Image 5",
        null=True,
        blank=True,
    )
    image6 = models.ImageField(
        upload_to="hostels/defaults/",
        verbose_name="Default Image 6",
        null=True,
        blank=True,
    )
    image7 = models.ImageField(
        upload_to="hostels/defaults/",
        verbose_name="Default Image 7",
        null=True,
        blank=True,
    )
    image8 = models.ImageField(
        upload_to="hostels/defaults/",
        verbose_name="Default Image 8",
        null=True,
        blank=True,
    )
    image9 = models.ImageField(
        upload_to="hostels/defaults/",
        verbose_name="Default Image 9",
        null=True,
        blank=True,
    )
    image10 = models.ImageField(
        upload_to="hostels/defaults/",
        verbose_name="Default Image 10",
        null=True,
        blank=True,
    )

    alt_text = models.CharField(
        max_length=255,
        default="Default hostel image",
        help_text="Alt text used for all default images",
    )

    class Meta:
        verbose_name = "Default Hostel Image"
        verbose_name_plural = "Default Hostel Images"

    def save(self, *args, **kwargs):
        # Singleton: ensure only one row
        self.pk = 1
        fields = ["image1", "image2", "image3", "image4", "image5", "image6", "image7", "image8", "image9", "image10"]
        from Hbackend.utils import process_image_fields, delete_old_image_files
        delete_old_image_files(self, fields)
        process_image_fields(self, fields)
        
        # Pop force_insert to avoid IntegrityError in admin if pk=1 already exists
        kwargs.pop('force_insert', None)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Prevent deletion

    def __str__(self):
        return "Default Hostel Images"
