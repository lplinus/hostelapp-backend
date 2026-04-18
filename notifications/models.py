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
