import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from django.core.exceptions import ValidationError

from .models import GuestProfile, GuestDocument, validate_id_document
from .serializers import GuestProfileSerializer, GuestDocumentSerializer
from bookings.models import Booking
from hotels.models import HotelBooking
from vacanationrentals.models import VacationRentalBooking


def get_booking_occupancy(user, booking_ref):
    """
    Helper to look up allowed guest occupancy for a booking reference
    across Hostels, Hotels, and Vacation Rentals.
    """
    if not booking_ref:
        return None

    # 1. Hostel Booking
    try:
        hb = Booking.objects.filter(id=booking_ref).first()
        if hb and (hb.user == user or hb.guest_email == user.email):
            return hb.guests_count or getattr(hb, "adults", 1) or 1
    except Exception:
        pass

    # 2. Hotel Booking
    try:
        hotel_b = HotelBooking.objects.filter(booking_reference=booking_ref).first()
        if hotel_b and (hotel_b.user == user or (getattr(hotel_b, "guest_details", None) and hotel_b.guest_details.guest_email == user.email)):
            adults = getattr(hotel_b.guest_details, "adults_count", None) if hasattr(hotel_b, "guest_details") else None
            return adults or (hotel_b.number_of_rooms * 2) or 2
    except Exception:
        pass

    # 3. Vacation Rental Booking
    try:
        vrb = VacationRentalBooking.objects.filter(booking_reference=booking_ref).first()
        if vrb and (vrb.user == user or (getattr(vrb, "guest_details", None) and vrb.guest_details.guest_email == user.email)):
            return getattr(vrb, "total_guests", None) or getattr(vrb, "adults", None) or (getattr(vrb.rental, "max_guests", None) if hasattr(vrb, "rental") else 2) or 2
    except Exception:
        pass

    return None


class CurrentGuestProfileView(APIView):
    """
    Get or update the profile of the currently logged-in guest.
    Creates one on the fly if it does not yet exist.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        profile, _ = GuestProfile.objects.get_or_create(user=request.user)
        serializer = GuestProfileSerializer(profile, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile, _ = GuestProfile.objects.get_or_create(user=request.user)
        serializer = GuestProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GuestDocumentsView(APIView):
    """
    List and upload guest & member identity documents.
    Enforces configurable max_document_uploads and booking occupancy limits.
    Stores files securely on Bunny CDN with original filenames and document categories tracked separately.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        profile, _ = GuestProfile.objects.get_or_create(user=request.user)
        booking_ref = request.query_params.get("booking_ref", "").strip()

        # Base limit from superadmin settings or profile override
        max_allowed = profile.effective_max_document_uploads

        # If booking_ref provided, compute occupancy limit
        if booking_ref:
            occupancy = get_booking_occupancy(request.user, booking_ref)
            if occupancy and occupancy > 0:
                max_allowed = min(occupancy, max_allowed)
            docs = profile.documents.filter(is_deleted=0, booking_reference=booking_ref)
        else:
            docs = profile.documents.filter(is_deleted=0)

        serializer = GuestDocumentSerializer(docs, many=True, context={"request": request})
        doc_list = list(serializer.data)

        # Backward compatibility: include legacy primary aadhaar if not yet in GuestDocument
        if not any(d.get("is_primary_guest") for d in doc_list) and profile.aadhaar_card_file:
            legacy_item = {
                "id": str(profile.id),
                "is_primary_guest": True,
                "member_name": profile.full_name or "Primary Guest",
                "document_type": "aadhaar",
                "document_type_name": "Aadhaar Card",
                "document_number": profile.aadhaar_number or "",
                "file": profile.aadhaar_card_file.name,
                "file_url": profile.aadhaar_card_file.url,
                "file_name": profile.aadhaar_original_name or os.path.basename(profile.aadhaar_card_file.name),
                "file_size": 0,
                "booking_reference": "",
                "verification_status": profile.id_verification_status,
                "created_at": profile.created_at.isoformat() if profile.created_at else None,
                "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
            }
            doc_list.insert(0, legacy_item)

        uploaded_count = len(doc_list)
        remaining_slots = max(0, max_allowed - uploaded_count)

        return Response({
            "documents": doc_list,
            "max_allowed": max_allowed,
            "uploaded_count": uploaded_count,
            "remaining_slots": remaining_slots,
        }, status=status.HTTP_200_OK)

    def post(self, request):
        profile, _ = GuestProfile.objects.get_or_create(user=request.user)
        file_obj = request.FILES.get("file") or request.FILES.get("aadhaar_card_file")
        if not file_obj:
            return Response({"detail": "No document file was provided for upload."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate file format and size
        try:
            validate_id_document(file_obj)
        except ValidationError as e:
            msg = e.message if hasattr(e, "message") else str(e)
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

        is_primary_raw = request.data.get("is_primary_guest", "false")
        is_primary = str(is_primary_raw).lower() in ("true", "1", "yes")

        member_name = request.data.get("member_name", "").strip()
        if not member_name:
            member_name = profile.full_name or request.user.get_full_name() or "Primary Guest"

        document_type = request.data.get("document_type", "aadhaar").strip().lower()
        valid_types = [c[0] for c in GuestDocument.DocumentCategory.choices]
        if document_type not in valid_types:
            document_type = "other"

        document_number = request.data.get("document_number", "").strip()
        booking_ref = request.data.get("booking_reference", "").strip()

        # Limit enforcement from superadmin settings or profile override
        max_allowed = profile.effective_max_document_uploads
        if booking_ref:
            occupancy = get_booking_occupancy(request.user, booking_ref)
            if occupancy and occupancy > 0:
                max_allowed = min(occupancy, max_allowed)
            current_count = profile.documents.filter(is_deleted=0, booking_reference=booking_ref).count()
        else:
            current_count = profile.documents.filter(is_deleted=0).count()

        # Account for legacy primary aadhaar if not yet in GuestDocument table
        has_legacy_primary = bool(profile.aadhaar_card_file and not profile.documents.filter(is_deleted=0, is_primary_guest=True).exists())
        total_count = current_count + (1 if has_legacy_primary else 0)

        # If primary guest doc already exists, replace it
        if is_primary:
            existing_primary = profile.documents.filter(is_deleted=0, is_primary_guest=True).first()
            if existing_primary:
                # Purge old file from Bunny Storage
                if existing_primary.file:
                    try:
                        existing_primary.file.delete(save=False)
                    except Exception:
                        pass
                existing_primary.file = file_obj
                existing_primary.file_name = file_obj.name
                existing_primary.file_size = getattr(file_obj, "size", 0)
                existing_primary.member_name = member_name
                existing_primary.document_type = document_type
                if document_number:
                    existing_primary.document_number = document_number
                if booking_ref:
                    existing_primary.booking_reference = booking_ref
                existing_primary.verification_status = GuestDocument.VerificationStatus.VERIFIED
                existing_primary.save()

                profile.aadhaar_original_name = file_obj.name
                profile.id_verification_status = GuestProfile.VerificationStatus.VERIFIED
                profile.save(update_fields=["aadhaar_original_name", "id_verification_status"])

                serializer = GuestDocumentSerializer(existing_primary, context={"request": request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            elif has_legacy_primary:
                # Replacing legacy primary document does not increase count
                total_count = max(0, total_count - 1)

        # For member documents (or first primary doc), enforce upload limit
        if total_count >= max_allowed:
            return Response(
                {"detail": f"Upload limit reached. You can upload a maximum of {max_allowed} documents for this booking/profile."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create new document record with exact original file_name preserved
        doc = GuestDocument.objects.create(
            guest_profile=profile,
            is_primary_guest=is_primary,
            member_name=member_name,
            document_type=document_type,
            document_number=document_number,
            file=file_obj,
            file_name=file_obj.name,
            file_size=getattr(file_obj, "size", 0),
            booking_reference=booking_ref or None,
            verification_status=GuestDocument.VerificationStatus.VERIFIED,
        )

        if is_primary:
            profile.aadhaar_original_name = file_obj.name
            profile.id_verification_status = GuestProfile.VerificationStatus.VERIFIED
            profile.save(update_fields=["aadhaar_original_name", "id_verification_status"])

        serializer = GuestDocumentSerializer(doc, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class GuestDocumentDetailView(APIView):
    """
    Delete or update an individual guest/member document.
    Ensures file is completely purged from Bunny CDN and record is safely removed.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        profile, _ = GuestProfile.objects.get_or_create(user=request.user)
        try:
            doc = GuestDocument.objects.get(id=pk, guest_profile=profile, is_deleted=0)
        except GuestDocument.DoesNotExist:
            # Check legacy primary deletion
            if str(profile.id) == str(pk) and profile.aadhaar_card_file:
                try:
                    profile.aadhaar_card_file.delete(save=False)
                except Exception:
                    pass
                profile.aadhaar_card_file = None
                profile.aadhaar_original_name = None
                profile.id_verification_status = GuestProfile.VerificationStatus.UNVERIFIED
                profile.save()
                return Response({"detail": "Document deleted successfully."}, status=status.HTTP_200_OK)
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        # Purge file from Bunny Storage
        if doc.file:
            try:
                doc.file.delete(save=False)
            except Exception:
                pass

        is_primary = doc.is_primary_guest
        doc.delete()

        if is_primary:
            profile.aadhaar_card_file = None
            profile.aadhaar_original_name = None
            profile.id_verification_status = GuestProfile.VerificationStatus.UNVERIFIED
            profile.save(update_fields=["aadhaar_card_file", "aadhaar_original_name", "id_verification_status"])

        return Response({"detail": "Document deleted successfully."}, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        profile, _ = GuestProfile.objects.get_or_create(user=request.user)
        try:
            doc = GuestDocument.objects.get(id=pk, guest_profile=profile, is_deleted=0)
        except GuestDocument.DoesNotExist:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        member_name = request.data.get("member_name")
        if member_name and member_name.strip():
            doc.member_name = member_name.strip()

        document_type = request.data.get("document_type")
        if document_type:
            doc.document_type = document_type.strip().lower()

        document_number = request.data.get("document_number")
        if document_number is not None:
            doc.document_number = document_number.strip()

        doc.save()
        serializer = GuestDocumentSerializer(doc, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class GuestBookingsListView(APIView):
    """
    Consolidated bookings feed for the authenticated guest across:
    - Hostel Bookings
    - Hotel Bookings
    - Vacation Rental Bookings
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        email = user.email or ""
        phone = getattr(user, "phone", "") or ""

        results = []

        # 1. Hostel Bookings
        hostel_filter = Q(user=user)
        if email:
            hostel_filter |= Q(guest_email__iexact=email)
        if phone:
            hostel_filter |= Q(mobile_number=phone)

        hostel_bookings = (
            Booking.objects.filter(hostel_filter)
            .select_related("hostel", "room_type", "review")
            .order_by("-created_at")[:50]
        )

        for b in hostel_bookings:
            has_rev = hasattr(b, "review") and b.review is not None
            if b.room_type:
                if hasattr(b.room_type, "get_sharing_type_display") and hasattr(b.room_type, "get_room_category_display"):
                    room_title = f"{b.room_type.get_room_category_display()} ({b.room_type.get_sharing_type_display()})"
                elif hasattr(b.room_type, "name"):
                    room_title = b.room_type.name
                else:
                    room_title = str(b.room_type)
            else:
                room_title = "Standard Room"

            results.append({
                "id": str(b.id),
                "booking_type": "hostel",
                "booking_reference": getattr(b, "booking_reference", str(b.id)[:8].upper()),
                "property_id": b.hostel_id,
                "property_slug": b.hostel.slug if b.hostel else None,
                "property_name": b.hostel.name if b.hostel else "Hostel Stay",
                "room_title": room_title,
                "check_in": b.check_in.isoformat() if b.check_in else None,
                "check_out": b.check_out.isoformat() if b.check_out else None,
                "status": b.status,
                "total_price": str(b.total_price),
                "guests_count": b.guests_count,
                "payment_status": b.payment_status,
                "has_reviewed": has_rev,
                "review_rating": b.review.rating if has_rev else None,
                "review_comment": b.review.comment if has_rev else None,
                "created_at": b.created_at.isoformat() if hasattr(b, "created_at") and b.created_at else None,
            })

        # 2. Hotel Bookings
        hotel_filter = Q(user=user)
        if email:
            hotel_filter |= Q(guest_details__guest_email__iexact=email)
        if phone:
            hotel_filter |= Q(guest_details__mobile_number=phone)

        hotel_bookings = (
            HotelBooking.objects.filter(hotel_filter)
            .select_related("hotel", "room_type", "review")
            .order_by("-created_at")[:50]
        )

        for b in hotel_bookings:
            has_rev = hasattr(b, "review") and b.review is not None
            results.append({
                "id": str(b.id),
                "booking_type": "hotel",
                "booking_reference": b.booking_reference,
                "property_id": str(b.hotel_id) if b.hotel_id else None,
                "property_slug": b.hotel.slug if b.hotel else None,
                "property_name": b.hotel.name if b.hotel else "Hotel Stay",
                "room_title": getattr(b.room_type, "name", "Hotel Suite") if b.room_type else "Hotel Suite",
                "check_in": b.check_in_date.isoformat() if b.check_in_date else None,
                "check_out": b.check_out_date.isoformat() if b.check_out_date else None,
                "status": b.status,
                "total_price": str(b.total_amount),
                "guests_count": b.number_of_rooms,
                "payment_status": "confirmed",
                "has_reviewed": has_rev,
                "review_rating": b.review.rating if has_rev else None,
                "review_comment": b.review.comment if has_rev else None,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            })

        # 3. Vacation Rental Bookings
        vr_filter = Q(user=user)
        if email:
            vr_filter |= Q(guest_details__guest_email__iexact=email)
        if phone:
            vr_filter |= Q(guest_details__mobile_number=phone)

        vr_bookings = (
            VacationRentalBooking.objects.filter(vr_filter)
            .select_related("rental", "review")
            .order_by("-created_at")[:50]
        )

        for b in vr_bookings:
            has_rev = hasattr(b, "review") and b.review is not None
            results.append({
                "id": str(b.id),
                "booking_type": "vacation_rental",
                "booking_reference": b.booking_reference,
                "property_id": str(b.rental_id) if b.rental_id else None,
                "property_slug": b.rental.slug if b.rental else None,
                "property_name": b.rental.title if b.rental else "Vacation Home",
                "room_title": "Entire Place",
                "check_in": b.check_in_date.isoformat() if b.check_in_date else None,
                "check_out": b.check_out_date.isoformat() if b.check_out_date else None,
                "status": b.status,
                "total_price": str(b.total_price),
                "guests_count": 1,
                "payment_status": "confirmed",
                "has_reviewed": has_rev,
                "review_rating": b.review.rating if has_rev else None,
                "review_comment": b.review.comment if has_rev else None,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            })

        # Sort combined results descending by created_at or check_in
        results.sort(key=lambda x: x.get("created_at") or "", reverse=True)

        return Response(results, status=status.HTTP_200_OK)


class StaffVerifyGuestDocView(APIView):
    """
    Staff / Hostel Owner endpoint to verify or review a guest's Aadhaar & member
    documents directly from a booking reference for seamless check-in.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_ref):
        user = request.user

        def can_view(booking_user, owner_ids):
            return user.is_staff or booking_user == user or user.id in owner_ids

        # Find booking across hostel, hotel, or vacation rental
        hostel_booking = None
        try:
            hostel_booking = (
                Booking.objects.select_related("hostel", "user").filter(id=booking_ref).first()
            )
        except (ValueError, ValidationError):
            pass

        guest_profile = None
        if hostel_booking and hostel_booking.user:
            if not can_view(
                hostel_booking.user,
                {hostel_booking.owner_id, hostel_booking.hostel.owner_id},
            ):
                return Response(
                    {"detail": "You do not have permission to view this guest's documents."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            guest_profile = getattr(hostel_booking.user, "guest_profile", None)

        if not guest_profile:
            hotel_booking = (
                HotelBooking.objects.select_related("hotel", "user")
                .filter(booking_reference=booking_ref)
                .first()
            )
            if hotel_booking and hotel_booking.user:
                if not can_view(
                    hotel_booking.user,
                    {hotel_booking.owner_id, hotel_booking.hotel.owner_id},
                ):
                    return Response(
                        {"detail": "You do not have permission to view this guest's documents."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                guest_profile = getattr(hotel_booking.user, "guest_profile", None)

        if not guest_profile:
            try:
                vr_booking = (
                    VacationRentalBooking.objects.select_related("rental", "user")
                    .filter(booking_reference=booking_ref)
                    .first()
                )
                if vr_booking and vr_booking.user:
                    if not can_view(
                        vr_booking.user,
                        {vr_booking.owner_id, vr_booking.host_id, getattr(vr_booking.rental, "host_id", None)},
                    ):
                        return Response(
                            {"detail": "You do not have permission to view this guest's documents."},
                            status=status.HTTP_403_FORBIDDEN,
                        )
                    guest_profile = getattr(vr_booking.user, "guest_profile", None)
            except Exception:
                pass

        if not guest_profile:
            return Response(
                {"detail": "Guest profile not found for this booking."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not user.is_staff and guest_profile.user != user and not guest_profile.share_id_with_host:
            return Response(
                {
                    "detail": "Guest has not authorized sharing ID document with the property owner.",
                    "is_shared": False,
                    "id_verification_status": guest_profile.id_verification_status,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = GuestProfileSerializer(guest_profile, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
