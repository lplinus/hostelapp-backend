from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Q
from django.core.exceptions import ValidationError

from .models import GuestProfile
from .serializers import GuestProfileSerializer
from bookings.models import Booking
from hotels.models import HotelBooking
from vacanationrentals.models import VacationRentalBooking


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
    Staff / Hostel Owner endpoint to verify or review a guest's Aadhaar
    document directly from a booking reference for seamless check-in.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_ref):
        user = request.user

        def can_view(booking_user, owner_ids):
            # Only staff, the property owner, or the guest themself may see ID documents
            return user.is_staff or booking_user == user or user.id in owner_ids

        # Find booking across hostel or hotel
        try:
            hostel_booking = (
                Booking.objects.select_related("hostel", "user").filter(id=booking_ref).first()
            )
        except (ValueError, ValidationError):
            # booking_ref is not a UUID (e.g. a hotel booking reference)
            hostel_booking = None

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
                from vacanationrentals.models import VacationRentalBooking
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

        # Ensure that non-staff property owners only see documents if guest has granted sharing authorization
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
