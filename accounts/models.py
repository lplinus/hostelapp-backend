from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import secrets
from django.contrib.auth.models import UserManager as DjangoUserManager
from Hbackend.base_models import SoftDeleteModel, SoftDeleteManager
from Hbackend.utils import validate_image_size


class UserManager(DjangoUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=0)


class User(AbstractUser, SoftDeleteModel):
    ROLE_CHOICES = (
        ("guest", "Guest"),
        ("hostel_owner", "Hostel Owner"),
        ("vendor", "Vendor"),
        ("admin", "Admin"),
        ("superadmin", "Superadmin"),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="guest")
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True, validators=[validate_image_size])

    # Verification flags
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    # Keep legacy if needed, or use as global verified status
    is_verified = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        from Hbackend.utils import process_image_fields, delete_old_image_files
        delete_old_image_files(self, ["profile_picture"])
        process_image_fields(self, ["profile_picture"])
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


class VerificationCode(SoftDeleteModel):
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
        # Generate secure 6-digit code
        code = f"{secrets.randbelow(1000000):06d}"
        return cls.objects.create(user=user, code=code, type=type)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at


import os
from django.core.exceptions import ValidationError
from Hbackend.bunny_storage import bunny_storage


def validate_verification_document(file_obj):
    if not file_obj:
        return
    ext = os.path.splitext(file_obj.name)[1].lower()
    allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png", ".webp"]
    if ext not in allowed_extensions:
        raise ValidationError(f"Unsupported file format '{ext}'. Please upload a PDF or an Image (JPG, PNG, WebP).")
    if hasattr(file_obj, "size") and file_obj.size > 5 * 1024 * 1024:
        raise ValidationError("File size exceeds 5MB limit. Please upload a document smaller than or equal to 5MB.")


def verification_document_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    user_id = "user"
    if hasattr(instance, "verification") and instance.verification and instance.verification.user_id:
        user_id = str(instance.verification.user_id)
    unique_suffix = secrets.token_hex(4)
    return f"verification_documents/{user_id}/doc_{unique_suffix}{ext}"


class DocumentVerification(SoftDeleteModel):
    class RoleChoices(models.TextChoices):
        OWNER = "owner", "Owner"
        VENDOR = "vendor", "Vendor"
        SERVICE = "service", "Service"

    class VerificationStatus(models.TextChoices):
        UNVERIFIED = "unverified", "Unverified"
        PENDING = "pending", "Under Review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="document_verifications"
    )
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.OWNER
    )
    status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.UNVERIFIED
    )
    admin_notes = models.TextField(blank=True, null=True, help_text="Notes or feedback from Super Admin")
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="verified_document_verifications"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Document Verification"
        verbose_name_plural = "Document Verifications"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()}) - {self.get_status_display()}"

    def update_status(self):
        """
        Recalculates overall verification status based on its uploaded documents.
        - If no documents exist -> UNVERIFIED.
        - If any document is REJECTED -> REJECTED.
        - If any document is PENDING -> PENDING.
        - If all documents (at least 1) are VERIFIED -> VERIFIED.
        Also automatically synchronizes user.is_verified when verified!
        """
        docs = self.documents.filter(is_deleted=0)
        if not docs.exists():
            self.status = self.VerificationStatus.UNVERIFIED
        elif docs.filter(status=VerificationDocument.DocumentStatus.REJECTED).exists():
            self.status = self.VerificationStatus.REJECTED
        elif docs.filter(status=VerificationDocument.DocumentStatus.PENDING).exists():
            self.status = self.VerificationStatus.PENDING
        elif docs.filter(status=VerificationDocument.DocumentStatus.VERIFIED).exists():
            self.status = self.VerificationStatus.VERIFIED
            self.verified_at = timezone.now()
            # Synchronize user is_verified
            if not self.user.is_verified:
                self.user.is_verified = True
                self.user.save(update_fields=["is_verified"])
        self.save(update_fields=["status", "verified_at", "updated_at"])


class VerificationDocument(SoftDeleteModel):
    class DocumentStatus(models.TextChoices):
        PENDING = "pending", "Under Review"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    class DocumentType(models.TextChoices):
        # Owner documents
        PROPERTY_DEED = "property_deed", "Property Deed / Ownership Proof"
        BUSINESS_LICENSE = "business_license", "Business / Trade License"
        TAX_PAN = "tax_pan", "PAN / Tax ID"
        UTILITY_BILL = "utility_bill", "Utility / Electricity Bill"
        GOVT_ID = "govt_id", "Owner Govt ID (Aadhaar / Passport)"
        # Vendor documents
        VENDOR_LICENSE = "vendor_license", "Shop & Establishment License"
        FSSAI_CERT = "fssai_cert", "FSSAI Registration Certificate"
        GSTIN_CERT = "gstin_cert", "GSTIN Document"
        MERCHANT_ID = "merchant_id", "Merchant Aadhaar / Govt ID"
        # Service provider documents
        SERVICE_CERT = "service_cert", "Trade / Professional Certificate"
        POLICE_CLEARANCE = "police_clearance", "Police Verification / Clearance"
        SERVICE_ID = "service_id", "Service Provider Govt ID"
        OTHER = "other", "Other Supporting Document"

    verification = models.ForeignKey(
        DocumentVerification,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        default=DocumentType.PROPERTY_DEED
    )
    title = models.CharField(max_length=255, help_text="Descriptive title for this document")
    file = models.FileField(
        upload_to=verification_document_upload_path,
        storage=bunny_storage,
        validators=[validate_verification_document],
        help_text="Uploaded document file (PDF, JPG, PNG, WEBP, max 5MB stored on Bunny CDN)"
    )
    file_size = models.PositiveIntegerField(default=0, help_text="File size in bytes")
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING
    )
    rejection_reason = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Verification Document"
        verbose_name_plural = "Verification Documents"

    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()}) - {self.get_status_display()}"

    def clean(self):
        super().clean()
        if not self.pk:
            current_count = VerificationDocument.objects.filter(
                verification=self.verification,
                is_deleted=0
            ).count()
            if current_count >= 5:
                raise ValidationError("You can upload a maximum of 5 verification documents.")

    def save(self, *args, **kwargs):
        if hasattr(self.file, "_file") and self.file._file and hasattr(self.file._file, "size"):
            self.file_size = self.file._file.size
        super().save(*args, **kwargs)
        if self.verification:
            self.verification.update_status()

    def delete(self, *args, **kwargs):
        verification = self.verification
        if self.file and hasattr(self.file, "name"):
            try:
                bunny_storage.delete(self.file.name)
            except Exception:
                pass
        super().delete(*args, **kwargs)
        if verification:
            verification.update_status()


