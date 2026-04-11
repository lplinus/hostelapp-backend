from django.db import models
from django.utils.text import slugify


# Terms and Conditions

class TermsAndConditions(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    effective_date = models.DateField()
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Terms and Conditions"
        verbose_name_plural = "Terms and Conditions"

    def __str__(self):
        return self.title



# Privacy Policy

class PrivacyPolicy(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    effective_date = models.DateField()
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Privacy Policy"
        verbose_name_plural = "Privacy Policies"

    def __str__(self):
        return self.title



#Faqs
class FAQCategory(models.Model):
    """
    FAQ categories for grouping questions
    Example:
    - Booking
    - Payments
    - Hostel Facilities
    - Cancellation
    """

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "FAQ Category"
        verbose_name_plural = "FAQ Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class FAQ(models.Model):
    """
    Main FAQ model
    """

    category = models.ForeignKey(
        FAQCategory,
        on_delete=models.CASCADE,
        related_name="faqs"
    )

    question = models.CharField(max_length=300)
    answer = models.TextField()

    slug = models.SlugField(unique=True, blank=True)

    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # SEO fields
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)

    # Analytics
    view_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.question[:70])
        super().save(*args, **kwargs)

    def __str__(self):
        return self.question


class StorageSettings(models.Model):
    PROVIDER_IMAGEKIT = "imagekit"
    PROVIDER_CLOUDINARY = "cloudinary"

    PROVIDER_CHOICES = [
        (PROVIDER_IMAGEKIT, "ImageKit (Primary) + Cloudinary (Fallback)"),
        (PROVIDER_CLOUDINARY, "Cloudinary (Primary) + ImageKit (Fallback)"),
    ]

    max_image_size_mb = models.PositiveIntegerField(
        default=10,
        help_text="Global maximum size for image uploads in MB.",
    )

    image_storage_provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_IMAGEKIT,
        help_text=(
            "Select the primary image storage service for hostel images. "
            "The other service acts as automatic fallback if the primary fails."
        ),
    )

    class Meta:
        verbose_name = "Storage Settings"
        verbose_name_plural = "Storage Settings"

    def save(self, *args, **kwargs):
        # Singleton — always pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Storage Settings | Provider: {self.get_image_storage_provider_display()} "
            f"| Max Size: {self.max_image_size_mb} MB"
        )

    @classmethod
    def get_active_provider(cls):
        """
        Returns the active image storage provider string ('imagekit' or 'cloudinary').
        Falls back to the Django settings value if the DB row doesn't exist yet.
        """
        try:
            obj = cls.objects.get(pk=1)
            return obj.image_storage_provider
        except cls.DoesNotExist:
            from django.conf import settings
            return getattr(settings, "IMAGE_STORAGE_PROVIDER", cls.PROVIDER_IMAGEKIT)