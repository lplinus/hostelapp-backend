from django.db import models
from django.conf import settings
from Hbackend.base_models import SoftDeleteModel
from Hbackend.utils import validate_image_size, process_image_fields, delete_old_image_files
from hostels.models import Hostel
from vendors.models import Vendor
from marketplace.models import Product

class Order(SoftDeleteModel):
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted by Vendor"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "In Transit"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class OrderType(models.TextChoices):
        STRUCTURED = "structured", "Structured Catalog Order"
        IMAGE_SCAN = "image_scan", "Image/List Scan"

    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.CASCADE,
        related_name="orders",
        db_index=True
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.CASCADE,
        related_name="received_orders",
        db_index=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
        db_index=True
    )
    order_type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
        default=OrderType.STRUCTURED,
        db_index=True
    )
    
    # For Image/List Scan Orders
    scan_image = models.ImageField(
        upload_to="orders/scans/",
        null=True,
        blank=True,
        validators=[validate_image_size]
    )
    note = models.TextField(blank=True, null=True, help_text="Additional instructions")

    total_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0.0
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        delete_old_image_files(self, ["scan_image"])
        process_image_fields(self, ["scan_image"])
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Order #{self.id} - {self.hostel.name} → {self.vendor.business_name}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['hostel', 'status']),
            models.Index(fields=['vendor', 'status']),
        ]

class OrderItem(SoftDeleteModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    product_name_at_order = models.CharField(max_length=255) # Snapshot
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=15, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total_price = (self.quantity or 0) * (self.unit_price or 0)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product_name_at_order} (Order #{self.order_id})"
