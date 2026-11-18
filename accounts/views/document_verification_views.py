from datetime import timedelta
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from django.shortcuts import get_object_or_404

from accounts.models import DocumentVerification, VerificationDocument
from accounts.serializers.document_verification_serializer import (
    DocumentVerificationSerializer,
    VerificationDocumentSerializer,
    DocumentUploadSerializer,
)
from Hbackend.bunny_storage import bunny_storage

ROLE_DOCUMENT_TYPES = {
    DocumentVerification.RoleChoices.OWNER: [
        {"value": "property_deed", "label": "Property Ownership / Lease Deed", "description": "Title deed, registered lease agreement, or property tax receipt"},
        {"value": "business_license", "label": "Trade / Business License", "description": "Municipal trade license, shop & establishment certificate"},
        {"value": "tax_pan", "label": "PAN / GSTIN Document", "description": "Business or owner PAN card, GST registration certificate"},
        {"value": "utility_bill", "label": "Utility / Electricity Bill", "description": "Recent electricity, water, or commercial broadband bill (within 3 months)"},
        {"value": "govt_id", "label": "Owner Govt ID (Aadhaar / Passport)", "description": "Government issued identity proof of the primary owner"},
        {"value": "other", "label": "Other Supporting Document", "description": "NOC, fire safety certificate, or tourism department approval"},
    ],
    DocumentVerification.RoleChoices.VENDOR: [
        {"value": "vendor_license", "label": "Shop & Establishment / Trade License", "description": "Local municipal trade license or shop registration"},
        {"value": "fssai_cert", "label": "FSSAI Food Safety License", "description": "Mandatory for Kirana and packaged food merchants"},
        {"value": "gstin_cert", "label": "GSTIN Registration Certificate", "description": "Official GST certificate if registered"},
        {"value": "tax_pan", "label": "Business / Proprietor PAN", "description": "Permanent Account Number card copy"},
        {"value": "merchant_id", "label": "Merchant Govt ID (Aadhaar / Passport)", "description": "Identity proof of the registered merchant"},
        {"value": "other", "label": "Other Supporting Document", "description": "Bank passbook, merchant agreement, etc."},
    ],
    DocumentVerification.RoleChoices.SERVICE: [
        {"value": "service_cert", "label": "Professional / Trade Certification", "description": "Skill certification, trade license, or vocational diploma"},
        {"value": "police_clearance", "label": "Police Verification / Background Check", "description": "Clearance certificate for on-premise service delivery"},
        {"value": "tax_pan", "label": "Service Provider PAN", "description": "Permanent Account Number card copy"},
        {"value": "service_id", "label": "Service Provider Govt ID", "description": "Government issued identity proof (Aadhaar/Voter ID/Passport)"},
        {"value": "other", "label": "Other Supporting Document", "description": "Work reference, experience certificate, etc."},
    ],
}


def resolve_user_verification_role(user):
    """
    Automatically resolves the verification role based on the logged-in user's role.
    - 'hostel_owner', 'owner', 'admin', 'superadmin', 'guest' -> 'owner'
    - 'vendor' -> 'vendor'
    - 'service', 'service_provider' -> 'service'
    """
    user_role = getattr(user, "role", "owner")
    if user_role in ["hostel_owner", "owner", "admin", "superadmin", "guest"]:
        return DocumentVerification.RoleChoices.OWNER
    elif user_role == "vendor":
        return DocumentVerification.RoleChoices.VENDOR
    elif user_role in ["service", "service_provider"]:
        return DocumentVerification.RoleChoices.SERVICE
    return DocumentVerification.RoleChoices.OWNER


class OwnerDocumentVerificationView(APIView):
    """
    GET: Retrieve current user's document verification container and list of documents.
    The role is automatically inferred from the authenticated user's role.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = resolve_user_verification_role(user)

        verification, _ = DocumentVerification.objects.get_or_create(
            user=user,
            role=role,
            is_deleted=0,
            defaults={"status": DocumentVerification.VerificationStatus.UNVERIFIED}
        )

        serializer = DocumentVerificationSerializer(verification, context={"request": request})
        data = serializer.data
        data["detected_role"] = role
        data["allowed_document_types"] = ROLE_DOCUMENT_TYPES.get(
            role,
            ROLE_DOCUMENT_TYPES[DocumentVerification.RoleChoices.OWNER]
        )
        return Response(data, status=status.HTTP_200_OK)


class OwnerDocumentUploadView(APIView):
    """
    POST: Upload a single verification document to Bunny CDN (up to 5 documents max, <= 5MB).
    Role is automatically inferred from the logged-in user.
    Title and Document Type are optional (fallbacks provided automatically).
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user
        role = resolve_user_verification_role(user)

        verification, _ = DocumentVerification.objects.get_or_create(
            user=user,
            role=role,
            is_deleted=0,
            defaults={"status": DocumentVerification.VerificationStatus.UNVERIFIED}
        )

        # Check document count limit
        current_count = verification.documents.filter(is_deleted=0).count()
        if current_count >= 5:
            return Response(
                {"error": "Maximum upload limit reached. You can upload a maximum of 5 documents."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        uploaded_file = validated_data["file"]

        # Automatic fallback for title if not provided
        raw_title = validated_data.get("title", "").strip()
        if not raw_title:
            name_part = uploaded_file.name.rsplit(".", 1)[0]
            raw_title = name_part.replace("_", " ").replace("-", " ").strip()
            if not raw_title:
                raw_title = "Verification Document"

        # Automatic fallback for document_type if not provided
        doc_type = validated_data.get("document_type", "").strip()
        allowed_list = ROLE_DOCUMENT_TYPES.get(role, ROLE_DOCUMENT_TYPES[DocumentVerification.RoleChoices.OWNER])
        valid_type_values = [d["value"] for d in allowed_list]
        if not doc_type or doc_type not in valid_type_values:
            doc_type = valid_type_values[0] if valid_type_values else "property_deed"

        doc = VerificationDocument.objects.create(
            verification=verification,
            title=raw_title,
            document_type=doc_type,
            file=uploaded_file,
            file_size=uploaded_file.size,
            status=VerificationDocument.DocumentStatus.PENDING
        )

        verification.update_status()

        verification_data = DocumentVerificationSerializer(verification, context={"request": request}).data
        verification_data["detected_role"] = role
        verification_data["allowed_document_types"] = allowed_list

        return Response(
            {
                "message": "Document uploaded to Bunny CDN successfully for review.",
                "document": VerificationDocumentSerializer(doc, context={"request": request}).data,
                "verification": verification_data
            },
            status=status.HTTP_201_CREATED
        )


class OwnerDocumentDeleteView(APIView):
    """
    DELETE: Remove an uploaded document from the current user's verification (deleting from Bunny CDN).
    Enforces user isolation, 10-minute cooldown period, and prevents deletion once verified.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, document_id):
        user = request.user
        # Strict user isolation: query must belong to request.user
        doc = get_object_or_404(
            VerificationDocument,
            id=document_id,
            verification__user=user,
            is_deleted=0
        )

        # Prevent deleting if already verified
        if doc.status == VerificationDocument.DocumentStatus.VERIFIED or (doc.verification and doc.verification.status == DocumentVerification.VerificationStatus.VERIFIED):
            return Response(
                {"error": "Verified documents cannot be deleted. You can view your document at any time. If you need updates, please contact support."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 10-minute cooldown check (unless rejected, which can always be replaced)
        if doc.created_at and doc.status != VerificationDocument.DocumentStatus.REJECTED:
            elapsed = timezone.now() - doc.created_at
            if elapsed > timedelta(minutes=10):
                return Response(
                    {"error": "The 10-minute deletion grace period has expired for this document. It is locked for review. You can continue to view it at any time."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        verification = doc.verification
        role = resolve_user_verification_role(user)

        # Purge from Bunny CDN storage
        if doc.file and hasattr(doc.file, "name"):
            try:
                bunny_storage.delete(doc.file.name)
            except Exception:
                pass

        doc.delete()
        verification.update_status()

        verification_data = DocumentVerificationSerializer(verification, context={"request": request}).data
        verification_data["detected_role"] = role
        verification_data["allowed_document_types"] = ROLE_DOCUMENT_TYPES.get(
            role,
            ROLE_DOCUMENT_TYPES[DocumentVerification.RoleChoices.OWNER]
        )

        return Response(
            {
                "message": "Document removed and purged from Bunny CDN successfully.",
                "verification": verification_data
            },
            status=status.HTTP_200_OK
        )


class SuperAdminVerificationListView(APIView):
    """
    GET: Super Admin lists all document verifications across all roles.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        role_filter = request.query_params.get("role")
        status_filter = request.query_params.get("status")

        qs = DocumentVerification.objects.filter(is_deleted=0).select_related("user").prefetch_related("documents")
        if role_filter:
            qs = qs.filter(role=role_filter)
        if status_filter:
            qs = qs.filter(status=status_filter)

        serializer = DocumentVerificationSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SuperAdminDocumentActionView(APIView):
    """
    POST: Super Admin approves or rejects an individual document.
    """
    permission_classes = [IsAdminUser]
    parser_classes = [JSONParser, FormParser]

    def post(self, request, document_id):
        doc = get_object_or_404(VerificationDocument, id=document_id, is_deleted=0)
        action = request.data.get("action")  # 'verify' or 'reject'
        reason = request.data.get("rejection_reason", "").strip()

        if action == "verify":
            doc.status = VerificationDocument.DocumentStatus.VERIFIED
            doc.rejection_reason = None
            doc.save()
        elif action == "reject":
            doc.status = VerificationDocument.DocumentStatus.REJECTED
            doc.rejection_reason = reason or "Document does not satisfy verification criteria."
            doc.save()
        else:
            return Response(
                {"error": "Invalid action. Use 'verify' or 'reject'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        verification = doc.verification
        verification.verified_by = request.user
        verification.update_status()

        return Response(
            {
                "message": f"Document marked as {doc.get_status_display()}.",
                "document": VerificationDocumentSerializer(doc, context={"request": request}).data,
                "verification": DocumentVerificationSerializer(verification, context={"request": request}).data
            },
            status=status.HTTP_200_OK
        )
