from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import random


class User(AbstractUser):
    ROLE_CHOICES = (
        ("guest", "Guest"),
        ("hostel_owner", "Hostel Owner"),
        # ("admin", "Admin"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="guest")
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)

    # Verification flags
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    # Keep legacy if needed, or use as global verified status
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class VerificationCode(models.Model):
    TYPE_CHOICES = (
        ("email", "Email"),
        ("phone", "Phone"),
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="verification_codes"
    )
    code = models.CharField(max_length=6)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Code expires in 10 minutes
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    @classmethod
    def generate_code(cls, user, type):
        # Generate 6-digit code
        code = str(random.randint(100000, 999999))
        return cls.objects.create(user=user, code=code, type=type)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
