import os
import uuid
import re
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from Hbackend.base_models import SoftDeleteModel
from Hbackend.bunny_storage import bunny_storage


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


def guest_document_upload_path(instance, filename):
    """
    Store guest and member documents in Bunny Storage while preserving
    a clean version of the actual original filename.
    """
    clean_base = re.sub(r'[^a-zA-Z0-9_\.-]', '_', filename)
    guest_id = str(instance.guest_profile_id) if instance.guest_profile_id else "guest"
    member_folder = "primary" if instance.is_primary_guest else "members"
    unique_prefix = uuid.uuid4().hex[:8]
    return f"guest_documents/{guest_id}/{member_folder}/{unique_prefix}_{clean_base}"


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

    # Configurable Document Limit per guest (None = use superadmin global setting from Admin Panel)
    max_document_uploads = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=None,
        help_text="Maximum documents a guest can upload across self and members. Leave empty to use global setting from Django Admin.",
    )

    @property
    def effective_max_document_uploads(self):
        """
        Returns the active document limit for this guest.
        1. If an explicit custom override is set on this profile by the superadmin, use it.
        2. Otherwise, resolves to the global limit configured by superadmin in Django Admin (GuestDocumentSetting).
        3. Fallback to settings.MAX_GUEST_DOCUMENT_UPLOADS or 6.
        """
        if self.max_document_uploads is not None:
            return self.max_document_uploads
        try:
            return GuestDocumentSetting.get_setting().max_document_uploads
        except Exception:
            return getattr(
                settings,
                "MAX_GUEST_DOCUMENT_UPLOADS",
                getattr(settings, "GUEST_DOCUMENT_MAX_UPLOADS", 6),
            )

    # Legacy Aadhaar fields (maintained for backward compatibility)
    aadhaar_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Masked or full Aadhaar number (e.g. 1234 5678 9012)",
    )
    aadhaar_card_file = models.FileField(
        upload_to=guest_aadhaar_upload_path,
        storage=bunny_storage,
        blank=True,
        null=True,
        validators=[validate_id_document],
        help_text="Aadhaar Card copy in PDF or Image format (PNG, JPG, WebP) stored on Bunny CDN",
    )
    aadhaar_original_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Original uploaded filename with extension",
    )
    id_verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED,
    )
    share_id_with_host = models.BooleanField(
        default=False,
        help_text="Guest authorization to share Aadhaar details with property owner for check-in",
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

    def delete(self, *args, **kwargs):
        if self.aadhaar_card_file and self.aadhaar_card_file.name:
            try:
                bunny_storage.delete(self.aadhaar_card_file.name)
            except Exception:
                pass
        super().delete(*args, **kwargs)


class GuestDocument(SoftDeleteModel):
    """
    Stores individual identity documents for the primary guest and accompanying members/friends.
    Uploaded directly to Bunny CDN with the original file name and category tracked separately.
    """
    class DocumentCategory(models.TextChoices):
        AADHAAR = "aadhaar", "Aadhaar Card"
        PASSPORT = "passport", "Passport"
        DRIVING_LICENSE = "driving_license", "Driving License"
        VOTER_ID = "voter_id", "Voter ID"
        NATIONAL_ID = "national_id", "National ID"
        OTHER = "other", "Other Government ID"

    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Not Uploaded"
        PENDING = "pending", "Under Review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guest_profile = models.ForeignKey(
        GuestProfile,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    is_primary_guest = models.BooleanField(
        default=False,
        help_text="True if this is the primary guest's personal document (My Document)"
    )
    member_name = models.CharField(
        max_length=255,
        help_text="Full legal name of the primary guest or friend/member"
    )
    document_type = models.CharField(
        max_length=50,
        choices=DocumentCategory.choices,
        default=DocumentCategory.AADHAAR,
        help_text="Category of the document (separate from filename)"
    )
    document_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Optional identification number (e.g. Passport or Aadhaar number)"
    )
    file = models.FileField(
        upload_to=guest_document_upload_path,
        storage=bunny_storage,
        validators=[validate_id_document],
        help_text="Document file uploaded to Bunny CDN",
    )
    file_name = models.CharField(
        max_length=255,
        help_text="Original uploaded filename including extension"
    )
    file_size = models.PositiveIntegerField(
        default=0,
        help_text="File size in bytes"
    )
    booking_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Associated booking reference code if uploaded for a booking"
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.VERIFIED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary_guest", "created_at"]
        verbose_name = "Guest Document"
        verbose_name_plural = "Guest Documents"

    def __str__(self):
        role = "Primary" if self.is_primary_guest else "Member"
        return f"{self.member_name} ({role}) - {self.get_document_type_display()} [{self.file_name}]"

    def delete(self, *args, **kwargs):
        if self.file and self.file.name:
            try:
                bunny_storage.delete(self.file.name)
            except Exception:
                pass
        super().delete(*args, **kwargs)


class GuestDocumentSetting(models.Model):
    """
    Singleton setting managed directly in Django Admin by the Superadmin.
    Sets the global limit of identity documents a guest can upload (including primary guest and companion members).
    """
    max_document_uploads = models.PositiveIntegerField(
        default=6,
        help_text="Global maximum documents allowed per guest (including primary guest and companion members).",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Guest Document Setting"
        verbose_name_plural = "Guest Document Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_setting(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "max_document_uploads": getattr(
                    settings,
                    "MAX_GUEST_DOCUMENT_UPLOADS",
                    getattr(settings, "GUEST_DOCUMENT_MAX_UPLOADS", 6),
                )
            },
        )
        return obj

    def __str__(self):
        return f"Global Document Upload Limit: {self.max_document_uploads} documents"

