from django.db import models
from django.conf import settings
from Hbackend.base_models import SoftDeleteModel
from Hbackend.utils import validate_image_size, process_image_fields, delete_old_image_files

class Vendor(SoftDeleteModel):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vendor_profile",
        limit_choices_to={'role': 'vendor'}
    )
    business_name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(
        upload_to="vendors/logos/",
        null=True,
        blank=True,
        validators=[validate_image_size]
    )
    address = models.TextField()
    contact_phone = models.CharField(max_length=20)
    contact_email = models.EmailField()
    VENDOR_TYPE_CHOICES = [
    ('rice', 'Rice & Grains'),
    ('vegetables', 'Vegetables & Fruits'),
    ('dairy', 'Milk & Dairy Products'),
    ('eggs', 'Eggs'),
    ('meat', 'Meat & Poultry'),

    ('kirana', 'Kirana / General Store'),
    ('oil', 'Cooking Oil & Spices'),
    ('bakery', 'Bakery & Bread'),

    ('water', 'Drinking Water Supply'),
]

    vendor_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Selected vendor types/categories"
    )
    
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        delete_old_image_files(self, ["logo"])
        process_image_fields(self, ["logo"])
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.business_name

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['business_name', 'is_active']),
        ]
