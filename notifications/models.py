from django.db import models
from accounts.models import User
from Hbackend.base_models import SoftDeleteModel

class Notification(SoftDeleteModel):
    class NotificationType(models.TextChoices):
        BOOKING = 'booking', 'Booking Update'
        ORDER = 'order', 'Order Update'
        HOSTEL = 'hostel', 'Hostel Update'
        ROOM = 'room', 'Room Update'
        SYSTEM = 'system', 'System Alert'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    
    # Generic linkage to the object (e.g., a Booking UUID or Order ID) so frontend can route users correctly
    related_object_id = models.CharField(max_length=255, blank=True, null=True) 
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.title}"


class BroadcastNotification(models.Model):
    title = models.CharField(max_length=255, help_text="Title of the broadcast notification")
    message = models.TextField(help_text="Message body that will be sent to ALL users")
    link = models.CharField(max_length=255, blank=True, null=True, help_text="Optional: URL to redirect user when clicked")
    created_at = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False, help_text="True if it has been sent out to users")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"BROADCAST: {self.title}"


class VendorNotification(SoftDeleteModel):
    class NotificationType(models.TextChoices):
        ORDER = 'order', 'New Order Received'
        PAYMENT = 'payment', 'Payment Received'
        PRODUCT = 'product', 'Product Update'
        SYSTEM = 'system', 'System Alert'

    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name='vendor_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.ORDER)
    related_object_id = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.vendor.business_name} - {self.title}"
