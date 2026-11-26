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


class FCMDevice(models.Model):
    class DeviceType(models.TextChoices):
        WEB = 'web', 'Web Browser'
        ANDROID = 'android', 'Android'
        IOS = 'ios', 'iOS'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fcm_devices', null=True, blank=True)
    vendor = models.ForeignKey('vendors.Vendor', on_delete=models.CASCADE, related_name='fcm_devices', null=True, blank=True)
    registration_token = models.CharField(max_length=512, unique=True, db_index=True)
    device_type = models.CharField(max_length=20, choices=DeviceType.choices, default=DeviceType.WEB)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['vendor', 'is_active']),
        ]

    def __str__(self):
        owner = self.user.email if self.user else (self.vendor.business_name if self.vendor else 'Anonymous')
        return f"{owner} - {self.device_type} ({self.registration_token[:15]}...)"


# ==============================================================================
# 1-ON-1 HELP & SUPPORT CHAT MODELS (REST + POLLING, NO CHANNELS)
# ==============================================================================

class SupportThread(SoftDeleteModel):
    class Subject(models.TextChoices):
        BOOKING = 'booking', 'Booking Issue'
        PAYMENT = 'payment', 'Payment / Refund'
        COMPLAINT = 'complaint', 'Lodge a Complaint'
        OTHER = 'other', 'Other Inquiry'

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_threads')
    subject = models.CharField(max_length=30, choices=Subject.choices, default=Subject.OTHER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    last_message_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_message_at', '-created_at']
        verbose_name = 'Support Thread'
        verbose_name_plural = 'Support Threads'

    def __str__(self):
        return f"#{self.id} {self.user.email} ({self.get_subject_display()})"


class SupportMessage(SoftDeleteModel):
    thread = models.ForeignKey(SupportThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_messages')
    is_staff_reply = models.BooleanField(default=False)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Support Message'
        verbose_name_plural = 'Support Messages'

    def __str__(self):
        role = 'Support' if self.is_staff_reply else self.sender.email
        return f"{role}: {self.body[:40]}"

