from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import viewsets, permissions, decorators, status, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    VacationRental,
    VacationRentalImage,
    VacationRentalAvailability,
    VacationRentalBooking,
    VacationRentalGuest,
    VacationRentalPayment,
    VacationRentalCancellation,
)
from .serializers import (
    VacationRentalSerializer,
    VacationRentalWriteSerializer,
    VacationRentalImageSerializer,
    VacationRentalAvailabilitySerializer,
    VacationRentalBookingSerializer,
    VacationRentalBookingCreateSerializer,
)


class VacationRentalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vacation Rental property management & public discovery:
    - Public: list & retrieve active/approved vacation rentals.
    - Host: list, create, update, and manage owned properties.
    """
    queryset = (
        VacationRental.objects.select_related("city", "area", "host")
        .prefetch_related("amenities", "images")
        .all()
    )
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "city": ["exact"],
        "category": ["exact"],
        "rental_type": ["exact"],
        "max_guests": ["gte", "lte"],
        "bedrooms": ["gte", "lte"],
        "price_per_night": ["gte", "lte"],
        "instant_book": ["exact"],
        "allows_pets": ["exact"],
        "is_superhost": ["exact"],
        "is_featured": ["exact"],
    }
    search_fields = ["title", "city__name", "area__name", "address"]
    ordering_fields = ["price_per_night", "rating_avg", "created_at"]

    def get_queryset(self):
        qs = (
            VacationRental.objects.select_related("city", "area", "host")
            .prefetch_related("amenities", "images")
            .all()
        )
        if self.action in ["list", "retrieve"]:
            return qs.filter(is_active=True, is_approved=True)
        return qs

    def get_object(self):
        """Allows lookup by UUID (id) or slug for frontend navigation."""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_val = self.kwargs.get(self.lookup_field) or self.kwargs.get("id") or self.kwargs.get("pk")
        try:
            import uuid
            uuid.UUID(str(lookup_val))
            obj = get_object_or_404(queryset, id=lookup_val)
        except (ValueError, TypeError):
            obj = get_object_or_404(queryset, slug=lookup_val)

        self.check_object_permissions(self.request, obj)
        return obj

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return VacationRentalWriteSerializer
        return VacationRentalSerializer

    def perform_create(self, serializer):
        serializer.save(host=self.request.user, is_active=True, is_approved=True)

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="my-rentals")
    def my_rentals(self, request):
        """Returns all vacation rentals owned/hosted by the logged-in user."""
        rentals = (
            VacationRental.objects.filter(host=request.user)
            .select_related("city", "area", "host")
            .prefetch_related("amenities", "images")
        )
        serializer = VacationRentalSerializer(rentals, many=True, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="block-dates")
    def block_dates(self, request, slug=None):
        """Allows a host to block a date range on their property's calendar."""
        rental = self.get_object()
        if rental.host != request.user and not request.user.is_staff:
            return Response({"detail": "Only the host can block calendar dates."}, status=status.HTTP_403_FORBIDDEN)

        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        reason = request.data.get("reason", VacationRentalAvailability.BlockReason.HOST_RESERVED)

        if not start_date or not end_date:
            return Response({"detail": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

        from datetime import datetime
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        curr = start
        while curr <= end:
            VacationRentalAvailability.objects.update_or_create(
                rental=rental,
                date=curr,
                defaults={"is_available": False, "reason": reason},
            )
            curr += timedelta(days=1)

        return Response({"detail": f"Dates from {start} to {end} have been blocked successfully."})


class VacationRentalAvailabilityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing calendar date availability and custom pricing overrides.
    """
    queryset = VacationRentalAvailability.objects.select_related("rental").all()
    serializer_class = VacationRentalAvailabilitySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["rental", "date", "is_available"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]


class VacationRentalImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vacation rental images (upload, list, and delete).
    """
    queryset = VacationRentalImage.objects.select_related("rental").all()
    serializer_class = VacationRentalImageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["rental"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_destroy(self, instance):
        instance.delete()

    def create(self, request, *args, **kwargs):
        rental_id = request.data.get("rental")
        if not rental_id:
            return Response({"detail": "rental id is required."}, status=status.HTTP_400_BAD_REQUEST)

        rental = get_object_or_404(VacationRental, id=rental_id)
        image_files = []
        for key in ["images", "images[]", "image"]:
            if key in request.FILES:
                image_files.extend(request.FILES.getlist(key))
        for key in sorted(request.FILES.keys()):
            if key not in ["images", "images[]", "image"] and ("image" in key.lower() or "photo" in key.lower() or "file" in key.lower()):
                image_files.extend(request.FILES.getlist(key))

        if not image_files:
            return Response({"detail": "No image files provided."}, status=status.HTTP_400_BAD_REQUEST)

        created = []
        existing_count = rental.images.count()
        for idx, file_obj in enumerate(image_files):
            img = VacationRentalImage.objects.create(
                rental=rental,
                image=file_obj,
                caption=f"{rental.title} Photo {existing_count + idx + 1}",
                order=existing_count + idx,
                is_primary=(existing_count == 0 and idx == 0),
            )
            created.append(VacationRentalImageSerializer(img, context={"request": request}).data)
        return Response(created, status=status.HTTP_201_CREATED)


class VacationRentalBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vacation Rental bookings:
    - Guests create reservations (instant book or pending host approval).
    - Hosts review, approve, or decline reservation requests.
    - Guests and hosts can view reservation history and cancel.
    """
    queryset = (
        VacationRentalBooking.objects.select_related(
            "rental", "host", "user", "guest_details", "pricing_details", "cancellation_details"
        )
        .order_by("-created_at")
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "status": ["exact"],
        "check_in_date": ["gte", "lte", "exact"],
        "check_out_date": ["gte", "lte", "exact"],
        "rental": ["exact"],
    }
    search_fields = ["booking_reference", "rental__title", "guest_details__guest_name", "guest_details__mobile_number"]
    ordering_fields = ["created_at", "check_in_date", "total_price"]

    def get_permissions(self):
        if self.action in [
            "create",
            "send_otp",
            "verify_otp",
            "send_email_otp",
            "verify_email_otp",
        ]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return VacationRentalBookingCreateSerializer
        return VacationRentalBookingSerializer

    def get_queryset(self):
        user = self.request.user
        qs = (
            VacationRentalBooking.objects.select_related(
                "rental", "host", "user", "owner", "guest_details", "pricing_details", "cancellation_details"
            )
            .order_by("-created_at")
        )
        if user.is_staff:
            return qs
        if user.is_authenticated:
            # User can see bookings they made OR bookings for rentals they host/own
            return qs.filter(Q(user=user) | Q(host=user) | Q(owner=user) | Q(rental__host=user))
        return qs.none()

    def create(self, request, *args, **kwargs):
        serializer = VacationRentalBookingCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        response_serializer = VacationRentalBookingSerializer(booking, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    # ── OTP Verification Actions (mirroring working hostel pipeline) ───────────────

    @decorators.action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny], url_path="send_otp")
    def send_otp(self, request):
        """Sends an OTP to the phone number for vacation rental booking verification."""
        phone = request.data.get("phone") or request.data.get("mobile_number")
        if not phone:
            return Response({"error": "phone is required"}, status=status.HTTP_400_BAD_REQUEST)

        from bookings.models import Booking
        has_prior_booking = (
            VacationRentalBooking.objects.filter(guest_details__mobile_number=phone, status__in=["confirmed", "checked_in", "completed"]).exists()
            or Booking.objects.filter(mobile_number=phone, status__in=["confirmed", "completed"]).exists()
        )
        if has_prior_booking:
            return Response({"message": "Phone number already verified via previous booking", "verified": True})

        from bookings.services.booking_otp_service import BookingOTPService
        try:
            BookingOTPService.send_booking_otp(phone)
            return Response({"message": "OTP sent successfully", "verified": False})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @decorators.action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny], url_path="verify_otp")
    def verify_otp(self, request):
        """Verifies phone OTP for vacation rental booking."""
        phone = request.data.get("phone") or request.data.get("mobile_number")
        code = request.data.get("code") or request.data.get("otp")
        if not phone or not code:
            return Response({"error": "phone and code are required"}, status=status.HTTP_400_BAD_REQUEST)

        from bookings.services.booking_otp_service import BookingOTPService
        if BookingOTPService.verify_booking_otp(phone, str(code).strip()):
            return Response({"message": "Phone verified successfully", "verified": True})
        return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

    @decorators.action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny], url_path="send_email_otp")
    def send_email_otp(self, request):
        """Sends an OTP to the email address for vacation rental booking verification."""
        email = request.data.get("email") or request.data.get("guest_email")
        guest_name = request.data.get("guest_name", "")
        if not email:
            return Response({"error": "email is required"}, status=status.HTTP_400_BAD_REQUEST)

        clean_email = email.strip().lower()
        if (
            request.user.is_authenticated
            and getattr(request.user, "is_email_verified", False)
            and request.user.email
            and request.user.email.strip().lower() == clean_email
        ):
            return Response({"message": "Email already verified via account", "verified": True})

        from bookings.services.booking_otp_service import BookingOTPService
        try:
            BookingOTPService.send_booking_email_otp(clean_email, guest_name=guest_name)
            return Response({"message": "OTP sent to your email successfully", "verified": False})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @decorators.action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny], url_path="verify_email_otp")
    def verify_email_otp(self, request):
        """Verifies email OTP for vacation rental booking."""
        email = request.data.get("email") or request.data.get("guest_email")
        code = request.data.get("code") or request.data.get("otp")
        if not email or not code:
            return Response({"error": "email and code are required"}, status=status.HTTP_400_BAD_REQUEST)

        clean_email = email.strip().lower()
        clean_code = str(code).strip()
        from bookings.services.booking_otp_service import BookingOTPService
        if BookingOTPService.verify_booking_email_otp(clean_email, clean_code):
            if request.user.is_authenticated and request.user.email and request.user.email.strip().lower() == clean_email:
                request.user.is_email_verified = True
                request.user.save(update_fields=["is_email_verified"])
            return Response({"message": "Email verified successfully", "verified": True})
        return Response({"error": "Invalid or expired OTP code"}, status=status.HTTP_400_BAD_REQUEST)

    # ── Owner / Host Dashboard Actions (ensuring bookings are not filtered out) ─

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="my-bookings")
    def my_bookings(self, request):
        """Returns vacation rental bookings for the current user or their hosted properties."""
        qs = self.get_queryset()
        status_param = request.query_params.get("status")
        if status_param and status_param != "all":
            qs = qs.filter(status=status_param)
        serializer = VacationRentalBookingSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="hosted-bookings")
    def hosted_bookings(self, request):
        """Returns reservation requests received by the host for their properties."""
        user = request.user
        qs = self.get_queryset().filter(Q(host=user) | Q(owner=user) | Q(rental__host=user))
        status_param = request.query_params.get("status")
        if status_param and status_param != "all":
            qs = qs.filter(status=status_param)
        serializer = VacationRentalBookingSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="owner")
    def owner(self, request):
        """Mirrors /api/bookings/owner/ so vacation rental bookings can be queried identically."""
        return self.hosted_bookings(request)

    @decorators.action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="checkin")
    def checkin(self, request):
        """Marks a vacation rental reservation as checked-in (mirroring hostel check-in action)."""
        booking_id = request.data.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        booking_id_str = str(booking_id).strip()
        try:
            if booking_id_str.upper().startswith("VRB-"):
                booking = VacationRentalBooking.objects.get(booking_reference=booking_id_str.upper())
            else:
                booking = VacationRentalBooking.objects.get(id=booking_id_str)
        except VacationRentalBooking.DoesNotExist:
            return Response({"error": "Vacation rental booking not found"}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.is_staff and booking.host != request.user and getattr(booking, "owner", None) != request.user and getattr(booking.rental, "host", None) != request.user:
            raise PermissionDenied("You do not have permission to check-in this vacation rental booking.")

        if booking.status == VacationRentalBooking.BookingStatus.CHECKED_IN:
            return Response({"error": "Booking already checked in"}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = VacationRentalBooking.BookingStatus.CHECKED_IN
        booking.save(update_fields=["status"])
        return Response({"message": "Check-in successful", "booking_id": booking.id})

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="approve")
    def approve(self, request, pk=None):
        """Host approves a pending reservation request and locks the calendar dates."""
        booking = get_object_or_404(VacationRentalBooking, id=pk)
        if booking.host != request.user and getattr(booking, "owner", None) != request.user and not request.user.is_staff:
            return Response({"detail": "Only the host can approve this booking."}, status=status.HTTP_403_FORBIDDEN)

        if booking.status != VacationRentalBooking.BookingStatus.PENDING_APPROVAL:
            return Response(
                {"detail": f"Cannot approve booking in '{booking.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = VacationRentalBooking.BookingStatus.CONFIRMED
        booking.save(update_fields=["status"])

        # Block dates on calendar
        curr = booking.check_in_date
        while curr < booking.check_out_date:
            VacationRentalAvailability.objects.update_or_create(
                rental=booking.rental,
                date=curr,
                defaults={"is_available": False, "reason": VacationRentalAvailability.BlockReason.BOOKED},
            )
            curr += timedelta(days=1)

        serializer = VacationRentalBookingSerializer(booking, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="decline")
    def decline(self, request, pk=None):
        """Host declines a pending reservation request."""
        booking = get_object_or_404(VacationRentalBooking, id=pk)
        if booking.host != request.user and getattr(booking, "owner", None) != request.user and not request.user.is_staff:
            return Response({"detail": "Only the host can decline this booking."}, status=status.HTTP_403_FORBIDDEN)

        if booking.status != VacationRentalBooking.BookingStatus.PENDING_APPROVAL:
            return Response(
                {"detail": f"Cannot decline booking in '{booking.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = VacationRentalBooking.BookingStatus.DECLINED
        booking.save(update_fields=["status"])

        serializer = VacationRentalBookingSerializer(booking, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancels a vacation rental reservation and frees the calendar dates."""
        booking = get_object_or_404(VacationRentalBooking, id=pk)
        is_guest = booking.user == request.user
        is_host = booking.host == request.user

        if not is_guest and not is_host and not request.user.is_staff:
            return Response({"detail": "You do not have permission to cancel this booking."}, status=status.HTTP_403_FORBIDDEN)

        if booking.status == VacationRentalBooking.BookingStatus.CANCELLED:
            return Response({"detail": "This booking is already cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get("reason", "Cancelled by user")

        booking.status = VacationRentalBooking.BookingStatus.CANCELLED
        booking.save(update_fields=["status"])

        # Free the calendar dates
        VacationRentalAvailability.objects.filter(
            rental=booking.rental,
            date__gte=booking.check_in_date,
            date__lt=booking.check_out_date,
            reason=VacationRentalAvailability.BlockReason.BOOKED,
        ).delete()

        # Create cancellation record
        cancelled_by = (
            VacationRentalCancellation.CancelledBy.GUEST
            if is_guest
            else VacationRentalCancellation.CancelledBy.HOST
        )
        VacationRentalCancellation.objects.create(
            booking=booking,
            cancellation_policy_applied=booking.rental.cancellation_policy,
            cancelled_by=cancelled_by,
            reason=reason,
            refund_amount=booking.total_price,
            refund_status=VacationRentalCancellation.RefundStatus.PENDING,
        )

        serializer = VacationRentalBookingSerializer(booking, context={"request": request})
        return Response(serializer.data)
