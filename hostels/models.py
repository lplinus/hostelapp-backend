from django.db import models
from locations.models import City, Area
from accounts.models import User
from Hbackend.utils import (
    process_image_fields,
    delete_old_image_files,
    validate_image_size,
)
from Hbackend.imagekit_storage import ImageKitStorage
from decimal import Decimal
import os
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from Hbackend.base_models import SoftDeleteModel


class Hostel(SoftDeleteModel):
    name = models.CharField(max_length=255)

    class HostelType(models.TextChoices):
        BOYS = "boys", "Boys Hostel"
        GIRLS = "girls", "Girls Hostel"
        CO_LIVING = "co_living", "Co-Living Hostel"
        WORKING_PROFESSIONAL = "working_professional", "WorkingProfessionalsHostel"
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

    class SuitableFor(models.TextChoices):
        STUDENT = "student", "Student"
        JOB_HOLDER = "job_holder", "Job Holder"
        WORKING_PROFESSIONAL = "working_professional", "Working Professional"
        BOTH = "both", "Both (Student & Professional)"
        ANYONE = "anyone", "Anyone"

    suitable_for = models.JSONField(
        default=list,
        blank=True,
        help_text="Selected suitable categories (student, job_holder, etc.)",
    )
    slug = models.SlugField(unique=True)

    # SEO Fields
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=500, blank=True, null=True)
    canonical_url = models.URLField(blank=True, null=True)
    og_image = models.ImageField(
        upload_to="seo/hostels/",
        max_length=500,
        null=True,
        blank=True,
        validators=[validate_image_size],
    )
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
    food_rating_avg = models.FloatField(default=0)
    room_rating_avg = models.FloatField(default=0)
    hostel_rating_avg = models.FloatField(default=0)
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

    def update_price_from_rooms(self):
        """
        Updates the hostel's price based on room types.
        Prioritizes the one marked 'show_this_price', otherwise takes the minimum base_price.
        """
        # We import here to avoid circular dependencies
        from rooms.models import RoomType

        rooms = RoomType.objects.filter(hostel=self)
        if not rooms.exists():
            return

        # Prioritize one marked 'show_this_price'
        selected_room = rooms.filter(show_this_price=True).first()
        if not selected_room:
            # Fallback to the one with the lowest price
            selected_room = rooms.order_by("base_price").first()

        if selected_room:
            self.price = selected_room.base_price

            # Daily price fallback (monthly / 30) consistent with frontend logic
            if selected_room.price_per_day:
                self.price_per_day = selected_room.price_per_day
            elif selected_room.base_price:
                self.price_per_day = (
                    selected_room.base_price / Decimal("30")
                ).quantize(Decimal("1."))
            else:
                self.price_per_day = None

            # Since the save() method also handles discounted pricing,
            # we must call super().save() or self.save() to trigger it.
            self.save(update_fields=["price", "price_per_day"])

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

        # Auto-mark the city as featured when hostel is featured or top-rated
        if (self.is_featured or self.is_toprated) and self.city_id:
            from locations.models import City

            City.objects.filter(id=self.city_id, is_featured=False).update(
                is_featured=True
            )

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

    # ── AI Content Generation Fields ─────────────────────────────────────
    ai_description = models.TextField(
        null=True,
        blank=True,
        help_text="AI-generated marketing description for this hostel.",
    )
    ai_hash = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        db_index=True,
        help_text="MD5 hash of key hostel fields. Used for change detection.",
    )
    ai_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last AI description generation.",
    )
    ai_version = models.PositiveSmallIntegerField(
        default=1,
        help_text="Prompt version. Increment to force regeneration across all hostels.",
    )

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

    image = models.ImageField(
        upload_to="hostel-type-images/",
        max_length=500,
        validators=[validate_image_size],
    )
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


def hostel_image_upload_path(instance, filename):
    hostel = getattr(instance, "hostel", None)
    if not hostel and getattr(instance, "hostel_id", None):
        hostel = Hostel.objects.filter(id=instance.hostel_id).first()
    hostel_name = slugify(hostel.name) if (hostel and getattr(hostel, "name", None)) else "hostel"
    ext = os.path.splitext(filename)[1].lower() or ".webp"
    base = os.path.splitext(os.path.basename(filename))[0]
    return f"hostels/{hostel_name}/{hostel_name}-{base}{ext}"


class HostelImage(SoftDeleteModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        upload_to=hostel_image_upload_path, max_length=500, validators=[validate_image_size]
    )
    image2 = models.ImageField(
        null=True, blank=True, upload_to=hostel_image_upload_path, max_length=500, validators=[validate_image_size]
    )
    image3 = models.ImageField(
        null=True, blank=True, upload_to=hostel_image_upload_path, max_length=500, validators=[validate_image_size]
    )
    image4 = models.ImageField(
        null=True, blank=True, upload_to=hostel_image_upload_path, max_length=500, validators=[validate_image_size]
    )
    image5 = models.ImageField(
        null=True, blank=True, upload_to=hostel_image_upload_path, max_length=500, validators=[validate_image_size]
    )
    image6 = models.ImageField(
        null=True, blank=True, upload_to=hostel_image_upload_path, max_length=500, validators=[validate_image_size]
    )
    image7 = models.ImageField(
        null=True, blank=True, upload_to=hostel_image_upload_path, max_length=500, validators=[validate_image_size]
    )
    image8 = models.ImageField(
        null=True, blank=True, upload_to=hostel_image_upload_path, max_length=500, validators=[validate_image_size]
    )
    image9 = models.ImageField(
        null=True, blank=True, upload_to=hostel_image_upload_path, max_length=500, validators=[validate_image_size]
    )
    image10 = models.ImageField(
        null=True, blank=True, upload_to=hostel_image_upload_path, max_length=500, validators=[validate_image_size]
    )

    alt_text = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    provider = models.CharField(
        max_length=20,
        choices=[("imagekit", "ImageKit"), ("cloudinary", "Cloudinary")],
        default="imagekit",
    )

    def save(self, *args, **kwargs):
        # Handle uploads through the service to support fallback in both API and Admin
        from .services import ImageUploadService
        from cms.models import StorageSettings

        fields = [
            "image",
            "image2",
            "image3",
            "image4",
            "image5",
            "image6",
            "image7",
            "image8",
            "image9",
            "image10",
        ]
        delete_old_image_files(self, fields)

        # Set provider from admin-configured active provider before upload loop
        self.provider = StorageSettings.get_active_provider()

        service = ImageUploadService()
        hostel_obj = getattr(self, "hostel", None)
        if not hostel_obj and getattr(self, "hostel_id", None):
            hostel_obj = Hostel.objects.filter(id=self.hostel_id).first()

        if hostel_obj and getattr(hostel_obj, "name", None):
            hostel_slug = slugify(hostel_obj.name)
        elif hostel_obj and getattr(hostel_obj, "slug", None):
            hostel_slug = hostel_obj.slug
        else:
            hostel_slug = f"hostel-{getattr(self, 'hostel_id', 'unknown')}"

        folder = f"hostels/{hostel_slug}"

        for field_name in fields:
            field_file = getattr(self, field_name)
            # Process only if it's a new file and not already a URL
            if field_file and hasattr(field_file, "file") and not str(field_file).startswith("http"):
                try:
                    orig_name = getattr(field_file, "name", field_name)
                    ext = os.path.splitext(orig_name)[1] or ".webp"
                    meaningful_name = f"{hostel_slug}-{field_name}{ext}"
                    result = service.upload_image(field_file, meaningful_name, folder=folder)
                    setattr(self, field_name, result["url"])
                    # Update provider from actual result (may differ if fallback triggered)
                    self.provider = result["provider"]
                except Exception as e:
                    print(f"DEBUG: HostelImage upload failed for {field_name}: {e}")
                    pass

        # We skip process_image_fields because our service handles the upload,
        # and URLs shouldn't be processed for WebP conversion again.
        super().save(*args, **kwargs)

    def delete_files_from_storage(self):
        """Hard delete all populated image files from remote storage (ImageKit / Cloudinary)."""
        from Hbackend.imagekit_storage import ImageKitStorage
        from Hbackend.cloudinary_storage import CloudinaryStorage
        ik_storage = ImageKitStorage()
        cl_storage = CloudinaryStorage()

        fields = [
            "image", "image2", "image3", "image4", "image5",
            "image6", "image7", "image8", "image9", "image10",
        ]
        for field_name in fields:
            val = getattr(self, field_name)
            if val:
                val_str = str(val)
                try:
                    if self.provider == "cloudinary" or "res.cloudinary.com" in val_str:
                        cl_storage.delete(val_str)
                    else:
                        ik_storage.delete(val_str)
                except Exception as e:
                    print(f"DEBUG: Error deleting hostel image {val_str}: {e}")

    def delete(self, *args, **kwargs):
        self.delete_files_from_storage()
        super().hard_delete(*args, **kwargs)

    def hard_delete(self, *args, **kwargs):
        self.delete_files_from_storage()
        super().hard_delete(*args, **kwargs)

    def __str__(self):
        return f"{self.hostel.name} Image"



class DefaultHostelImage(models.Model):
    """
    Singleton model — only one row should exist.
    Stores fallback images shown when a hostel has no images uploaded.
    Upload these via Django Admin → Hostels → Default Hostel Images.
    """

    image1 = models.ImageField(
        upload_to="hostels/defaults/",
        max_length=500,
        verbose_name="Default Image 1",
        null=True,
        blank=True,
        validators=[validate_image_size],
    )
    image2 = models.ImageField(
        upload_to="hostels/defaults/",
        max_length=500,
        verbose_name="Default Image 2",
        null=True,
        blank=True,
        validators=[validate_image_size],
    )
    image3 = models.ImageField(
        upload_to="hostels/defaults/",
        max_length=500,
        verbose_name="Default Image 3",
        null=True,
        blank=True,
        validators=[validate_image_size],
    )
    image4 = models.ImageField(
        upload_to="hostels/defaults/",
        max_length=500,
        verbose_name="Default Image 4",
        null=True,
        blank=True,
        validators=[validate_image_size],
    )
    image5 = models.ImageField(
        upload_to="hostels/defaults/",
        max_length=500,
        verbose_name="Default Image 5",
        null=True,
        blank=True,
        validators=[validate_image_size],
    )
    image6 = models.ImageField(
        upload_to="hostels/defaults/",
        max_length=500,
        verbose_name="Default Image 6",
        null=True,
        blank=True,
        validators=[validate_image_size],
    )
    image7 = models.ImageField(
        upload_to="hostels/defaults/",
        max_length=500,
        verbose_name="Default Image 7",
        null=True,
        blank=True,
        validators=[validate_image_size],
    )
    image8 = models.ImageField(
        upload_to="hostels/defaults/",
        max_length=500,
        verbose_name="Default Image 8",
        null=True,
        blank=True,
        validators=[validate_image_size],
    )
    image9 = models.ImageField(
        upload_to="hostels/defaults/",
        max_length=500,
        verbose_name="Default Image 9",
        null=True,
        blank=True,
        validators=[validate_image_size],
    )
    image10 = models.ImageField(
        upload_to="hostels/defaults/",
        max_length=500,
        verbose_name="Default Image 10",
        null=True,
        blank=True,
        validators=[validate_image_size],
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
        fields = [
            "image1",
            "image2",
            "image3",
            "image4",
            "image5",
            "image6",
            "image7",
            "image8",
            "image9",
            "image10",
        ]
        from Hbackend.utils import process_image_fields, delete_old_image_files

        delete_old_image_files(self, fields)
        process_image_fields(self, fields)

        # Pop force_insert to avoid IntegrityError in admin if pk=1 already exists
        kwargs.pop("force_insert", None)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # Prevent deletion

    def __str__(self):
        return "Default Hostel Images"


class Landmark(SoftDeleteModel):
    hostel = models.ForeignKey(
        Hostel, on_delete=models.CASCADE, related_name="landmarks"
    )
    name = models.CharField(max_length=255)
    distance = models.CharField(max_length=100, help_text="e.g., 500m or 1.2km")
    is_popular = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.distance}) - {self.hostel.name}"


class ExtraCharge(SoftDeleteModel):
    hostel = models.ForeignKey(
        Hostel, on_delete=models.CASCADE, related_name="extra_charges"
    )

    class ChargeType(models.TextChoices):
        ELECTRICITY = "electricity", "Electricity"
        WATER = "water", "Water"
        MAINTENANCE = "maintenance", "Maintenance"
        WIFI = "wifi", "WiFi"
        LAUNDRY = "laundry", "Laundry"
        OTHER = "other", "Other"

    charge_type = models.CharField(
        max_length=50,
        choices=ChargeType.choices,
        default=ChargeType.ELECTRICITY,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.get_charge_type_display()} - {self.amount} for {self.hostel.name}"
