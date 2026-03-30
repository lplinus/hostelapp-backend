from django.db import models
from django.utils.text import slugify
from Hbackend.base_models import SoftDeleteModel
from Hbackend.utils import validate_image_size, process_image_fields, delete_old_image_files
from vendors.models import Vendor

class Category(SoftDeleteModel):
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=120, unique=True)
    icon = models.ImageField(
        upload_to="marketplace/categories/", 
        null=True, 
        blank=True,
        validators=[validate_image_size]
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Hierarchy support if needed
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subcategories'
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]
        indexes = [
            models.Index(fields=['name', 'is_active']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        delete_old_image_files(self, ["icon"])
        process_image_fields(self, ["icon"])
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

class Product(SoftDeleteModel):
    category = models.ForeignKey(
        Category, 
        related_name="products", 
        on_delete=models.CASCADE
    )
    vendor = models.ForeignKey(
        Vendor,
        related_name="marketplace_products",
        on_delete=models.CASCADE,
        db_index=True
    )
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=280, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    image = models.ImageField(
        upload_to="marketplace/products/", 
        null=True, 
        blank=True,
        validators=[validate_image_size]
    )
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_featured", "-created_at"]
        indexes = [
            models.Index(fields=['name', 'price']),
            models.Index(fields=['is_active', 'is_featured']),
            models.Index(fields=['vendor', 'is_active']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        delete_old_image_files(self, ["image"])
        process_image_fields(self, ["image"])
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.name} ({self.vendor.business_name if self.vendor else 'N/A'})"
