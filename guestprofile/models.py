import os
import uuid
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from Hbackend.base_models import SoftDeleteModel


def validate_id_document(file_obj):
    """
    Validate that the uploaded identity document is either an image (JPG, PNG, WebP)
    or a PDF document, with a reasonable maximum file size (15MB).
    """
    if not file_obj:
        return
    
    ext = os.path.splitext(file_obj.name)[1].lower()
    allowed_extensions = [".jpg", ".jpeg", ".png", ".webp", ".pdf"]
    if ext not in allowed_extensions:
        raise ValidationError(f"Unsupported file format '{ext}'. Please upload a PDF or an image (JPG, PNG, WebP).")
    
    # 15MB limit
    if hasattr(file_obj, "size") and file_obj.size > 15 * 1024 * 1024:
        raise ValidationError("File size exceeds 15MB limit. Please upload a smaller document.")


def guest_aadhaar_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    user_id = instance.user_id or "common"
    unique_suffix = uuid.uuid4().hex[:8]
    return f"guest_documents/aadhaar/{user_id}/aadhaar_{unique_suffix}{ext}"


class GuestProfile(SoftDeleteModel):
    class GenderChoices(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Not Uploaded"
        PENDING = "pending", "Under Review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guest_profile",
    )

    # Personal info (synchronized with User)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=20,
        choices=GenderChoices.choices,
        default=GenderChoices.PREFER_NOT_TO_SAY,
    )
    nationality = models.CharField(max_length=50, default="Indian")

    # Address
    address_line = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)

    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True, null=True)

    # Aadhaar / ID Proof
    aadhaar_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Masked or full Aadhaar number (e.g. 1234 5678 9012)",
    )
    aadhaar_card_file = models.FileField(
        upload_to=guest_aadhaar_upload_path,
        blank=True,
        null=True,
        validators=[validate_id_document],
        help_text="Aadhaar Card copy in PDF or Image format (PNG, JPG, WebP)",
    )
    id_verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )
    verified_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Guest Profile"
        verbose_name_plural = "Guest Profiles"

    def __str__(self):
        name = self.full_name or (self.user.get_full_name() if self.user else "Guest")
        return f"GuestProfile: {name} ({self.user.username if self.user else ''})"

    def clean(self):
        super().clean()
        if self.aadhaar_card_file and self.id_verification_status == self.VerificationStatus.UNVERIFIED:
            self.id_verification_status = self.VerificationStatus.PENDING

    def save(self, *args, **kwargs):
        # Auto sync with User model if fields are empty
        if self.user:
            if not self.email and self.user.email:
                self.email = self.user.email
            if not self.phone_number and getattr(self.user, "phone", None):
                self.phone_number = self.user.phone
            user_full = self.user.get_full_name().strip()
            if not self.full_name and user_full:
                self.full_name = user_full
            elif not self.full_name and self.user.username:
                self.full_name = self.user.username
        super().save(*args, **kwargs)
