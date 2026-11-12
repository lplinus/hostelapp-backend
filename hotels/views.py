from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, decorators, status, filters
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Hotel,
    HotelRoomType,
    HotelImage,
    HotelBooking,
    HotelGuest,
    HotelPayment,
    HotelCancellation,
)
from .serializers import (
    HotelSerializer,
    HotelWriteSerializer,
    HotelRoomTypeSerializer,
    HotelImageSerializer,
    HotelBookingSerializer,
    HotelBookingCreateSerializer,
)


def _ensure_hotel_owner(user, hotel):
    """Only the hotel's owner (or staff) may modify the hotel and its rooms/images."""
    if not user.is_staff and getattr(hotel, "owner_id", None) != user.id:
        raise PermissionDenied("You do not own this hotel.")


class HotelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Hotel property management and public discovery.
    - Public: list & retrieve active/approved hotels.
    - Authenticated: create and manage hotel properties.
    """
    queryset = (
        Hotel.objects.select_related("city", "area")
        .prefetch_related("amenities", "images", "room_types")
        .all()
    )
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "city": ["exact"],
        "hotel_type": ["exact"],
        "star_rating": ["gte", "lte", "exact"],
        "starting_price_per_night": ["gte", "lte"],
        "is_featured": ["exact"],
        "is_toprated": ["exact"],
        "allows_pets": ["exact"],
    }
    search_fields = ["name", "city__name", "area__name", "address"]
    ordering_fields = ["starting_price_per_night", "rating_avg", "star_rating", "created_at"]

    def get_queryset(self):
        qs = (
            Hotel.objects.select_related("city", "area")
            .prefetch_related("amenities", "images", "room_types")
            .all()
        )
        if self.request.user and self.request.user.is_authenticated:
            return qs
        if self.action in ["list", "retrieve"]:
            # On public pages only show approved and active properties
            return qs.filter(is_active=True, is_approved=True)
        return qs

    def perform_create(self, serializer):
        kwargs = {"is_active": True, "is_approved": True}
        if self.request.user and self.request.user.is_authenticated:
            kwargs["owner"] = self.request.user
        serializer.save(**kwargs)

    def perform_update(self, serializer):
        obj = serializer.instance
        if not self.request.user.is_staff and obj.owner != self.request.user:
            raise PermissionDenied("You do not own this hotel.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_staff and instance.owner != self.request.user:
            raise PermissionDenied("You do not own this hotel.")
        instance.delete()

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="my-hotels")
    def my_hotels(self, request):
        """Returns hotels owned by the authenticated owner."""
        hotels = (
            Hotel.objects.filter(owner=request.user)
            .select_related("city", "area", "owner")
            .prefetch_related("amenities", "images", "room_types")
        )
        serializer = HotelSerializer(hotels, many=True, context={"request": request})
        return Response(serializer.data)

    def get_object(self):
        """Allow lookup by both UUID (id) and slug for flexible frontend routing."""
        queryset = self.filter_queryset(self.get_queryset())
        lookup_val = self.kwargs.get(self.lookup_field) or self.kwargs.get("id") or self.kwargs.get("pk")
        
        # Check if UUID lookup
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
            return HotelWriteSerializer
        return HotelSerializer

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny], url_path="featured")
    def featured(self, request):
        """Top featured hotels for home and landing pages."""
        hotels = self.get_queryset().filter(is_featured=True)[:6]
        serializer = HotelSerializer(hotels, many=True, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="add-room-type")
    def add_room_type(self, request, slug=None):
        """Adds a new room type to an existing hotel."""
        hotel = self.get_object()
        _ensure_hotel_owner(request.user, hotel)
        serializer = HotelRoomTypeSerializer(data={**request.data, "hotel": hotel.id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="upload-images")
    def upload_images(self, request, slug=None):
        """Uploads multiple hotel photos via multipart form data."""
        hotel = self.get_object()
        _ensure_hotel_owner(request.user, hotel)
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
        existing_count = hotel.images.count()
        for idx, file_obj in enumerate(image_files):
            img = HotelImage.objects.create(
                hotel=hotel,
                image=file_obj,
                alt_text=f"{hotel.name} Photo {existing_count + idx + 1}",
                order=existing_count + idx,
                is_primary=(existing_count == 0 and idx == 0),
            )
            created.append(HotelImageSerializer(img, context={"request": request}).data)
        return Response(created, status=status.HTTP_201_CREATED)


class HotelImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing hotel images (upload, list, and delete).
    """
    queryset = HotelImage.objects.select_related("hotel", "room_type").all()
    serializer_class = HotelImageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["hotel", "room_type"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_update(self, serializer):
        _ensure_hotel_owner(self.request.user, serializer.instance.hotel)
        serializer.save()

    def perform_destroy(self, instance):
        _ensure_hotel_owner(self.request.user, instance.hotel)
        instance.delete()

    def create(self, request, *args, **kwargs):
        hotel_id = request.data.get("hotel")
        if not hotel_id:
            return Response({"detail": "hotel id is required."}, status=status.HTTP_400_BAD_REQUEST)

        hotel = get_object_or_404(Hotel, id=hotel_id)
        _ensure_hotel_owner(request.user, hotel)
        room_type_id = request.data.get("room_type")
        room_type = None
        if room_type_id:
            room_type = HotelRoomType.objects.filter(id=room_type_id, hotel=hotel).first()

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
        existing_count = hotel.images.count()
        for idx, file_obj in enumerate(image_files):
            img = HotelImage.objects.create(
                hotel=hotel,
                room_type=room_type,
                image=file_obj,
                alt_text=f"{hotel.name} Photo {existing_count + idx + 1}",
                order=existing_count + idx,
                is_primary=(existing_count == 0 and idx == 0),
            )
            created.append(HotelImageSerializer(img, context={"request": request}).data)
        return Response(created, status=status.HTTP_201_CREATED)


class HotelRoomTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing hotel room types and inventories.
    """
    queryset = HotelRoomType.objects.select_related("hotel").prefetch_related("images").all()
    serializer_class = HotelRoomTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["hotel", "room_category", "bed_type", "is_available"]
    ordering_fields = ["base_price_per_night", "rooms_available"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        _ensure_hotel_owner(self.request.user, serializer.validated_data.get("hotel"))
        serializer.save()

    def perform_update(self, serializer):
        _ensure_hotel_owner(self.request.user, serializer.instance.hotel)
        serializer.save()

    def perform_destroy(self, instance):
        _ensure_hotel_owner(self.request.user, instance.hotel)
        instance.delete()


class HotelBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for hotel reservations:
    - Guests can create bookings atomically after OTP verification.
    - Owners & Guests can view bookings without filter exclusion.
    - Provides OTP verification endpoints mirroring the hostel booking pipeline.
    """
    queryset = (
        HotelBooking.objects.select_related(
            "hotel", "room_type", "user", "owner", "guest_details", "payment_details", "cancellation_details"
        )
        .order_by("-created_at")
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "status": ["exact"],
        "check_in_date": ["gte", "lte", "exact"],
        "check_out_date": ["gte", "lte", "exact"],
        "hotel": ["exact"],
    }
    search_fields = [
        "booking_reference",
        "hotel__name",
        "guest_details__guest_name",
        "guest_details__guest_email",
        "guest_details__mobile_number",
    ]
    ordering_fields = ["created_at", "check_in_date", "total_amount"]

    def get_permissions(self):
        if self.action in [
            "create",
            "send_otp",
            "verify_otp",
            "send_email_otp",
            "verify_email_otp",
            "check_availability",
        ]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return HotelBookingCreateSerializer
        return HotelBookingSerializer

    def get_queryset(self):
        user = self.request.user
        qs = (
            HotelBooking.objects.select_related(
                "hotel", "room_type", "user", "owner", "guest_details", "payment_details", "cancellation_details"
            )
            .order_by("-created_at")
        )
        if user.is_staff:
            return qs
        if user.is_authenticated:
            from django.db.models import Q
            return qs.filter(Q(user=user) | Q(owner=user) | Q(hotel__owner=user))
        return qs.none()

    # Direct PUT/PATCH/DELETE on a booking is limited to the property owner or staff.
    # Guests change their bookings through the dedicated actions (e.g. cancel).
    def _ensure_booking_manager(self, booking):
        user = self.request.user
        if user.is_staff or booking.owner_id == user.id or booking.hotel.owner_id == user.id:
            return
        raise PermissionDenied("You do not have permission to modify this booking.")

    def perform_update(self, serializer):
        self._ensure_booking_manager(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_booking_manager(instance)
        instance.delete()

    def create(self, request, *args, **kwargs):
        serializer = HotelBookingCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        # Offload concurrent hotel booking processing, notifications, and QR generation to Celery
        from django.db import transaction
        from .tasks import process_hotel_booking_task

        transaction.on_commit(
            lambda: process_hotel_booking_task.delay(str(booking.id))
        )

        response_serializer = HotelBookingSerializer(booking, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    # ── OTP Verification Actions (mirroring working hostel pipeline) ───────────────

    @decorators.action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny], url_path="send_otp")
    def send_otp(self, request):
        """Sends an OTP to the phone number for hotel booking verification."""
        phone = request.data.get("phone") or request.data.get("mobile_number")
        if not phone:
            return Response({"error": "phone is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Smart verification check
        from bookings.models import Booking
        has_prior_booking = (
            HotelBooking.objects.filter(guest_details__mobile_number=phone, status__in=["confirmed", "checked_in"]).exists()
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
        """Verifies phone OTP for hotel booking."""
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
        """Sends an OTP to the email address for hotel booking verification."""
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
        """Verifies email OTP for hotel booking."""
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

    # ── Owner Dashboard Actions (ensuring hotel bookings are not filtered out) ───

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="my-bookings")
    def my_bookings(self, request):
        """
        Returns hotel reservations for the current user.
        If the user is an owner, returns their hosted properties' bookings alongside any personal bookings.
        """
        qs = self.get_queryset()
        status_param = request.query_params.get("status")
        if status_param and status_param != "all":
            qs = qs.filter(status=status_param)
        serializer = HotelBookingSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="hosted-bookings")
    def hosted_bookings(self, request):
        """Returns bookings received by the owner for their hotels."""
        from django.db.models import Q
        qs = self.get_queryset().filter(Q(owner=request.user) | Q(hotel__owner=request.user))
        status_param = request.query_params.get("status")
        if status_param and status_param != "all":
            qs = qs.filter(status=status_param)
        serializer = HotelBookingSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="owner")
    def owner(self, request):
        """Mirrors /api/bookings/owner/ so hotel bookings can be queried identically."""
        return self.hosted_bookings(request)

    @decorators.action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="checkin")
    def checkin(self, request):
        """Marks a hotel reservation as checked-in (mirroring hostel check-in action)."""
        booking_id = request.data.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        booking_id_str = str(booking_id).strip()
        try:
            if booking_id_str.upper().startswith("HTL-"):
                booking = HotelBooking.objects.get(booking_reference=booking_id_str.upper())
            else:
                booking = HotelBooking.objects.get(id=booking_id_str)
        except HotelBooking.DoesNotExist:
            return Response({"error": "Hotel booking not found"}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.is_staff and booking.owner != request.user and getattr(booking.hotel, "owner", None) != request.user:
            raise PermissionDenied("You do not have permission to check-in this hotel booking.")

        if booking.status == HotelBooking.BookingStatus.CHECKED_IN:
            return Response({"error": "Booking already checked in"}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = HotelBooking.BookingStatus.CHECKED_IN
        booking.save(update_fields=["status"])

        if hasattr(booking, "payment_details") and booking.payment_details:
            if booking.payment_details.payment_method in [
                HotelPayment.PaymentMethod.PAY_AT_HOTEL,
                HotelPayment.PaymentMethod.ON_ARRIVAL,
            ]:
                booking.payment_details.payment_status = HotelPayment.PaymentStatus.PAID
                booking.payment_details.paid_at = timezone.now()
                booking.payment_details.save(update_fields=["payment_status", "paid_at"])

        return Response({"message": "Check-in successful", "booking_id": booking.id})

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancels a booking and restores room inventory."""
        booking = get_object_or_404(HotelBooking, id=pk)
        if not request.user.is_staff and booking.user != request.user and booking.owner != request.user:
            return Response({"detail": "You do not own this booking."}, status=status.HTTP_403_FORBIDDEN)

        if booking.status == HotelBooking.BookingStatus.CANCELLED:
            return Response({"detail": "This booking is already cancelled."}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get("reason", "Cancelled by user")

        booking.status = HotelBooking.BookingStatus.CANCELLED
        booking.save(update_fields=["status"])

        # Restore inventory
        room_type = booking.room_type
        room_type.rooms_available += booking.number_of_rooms
        room_type.save(update_fields=["rooms_available"])

        # Create cancellation record
        HotelCancellation.objects.create(
            booking=booking,
            cancelled_by=HotelCancellation.CancelledBy.GUEST if not request.user.is_staff else HotelCancellation.CancelledBy.HOTEL_ADMIN,
            reason=reason,
            refund_amount=booking.total_amount,
            refund_status=HotelCancellation.RefundStatus.PENDING,
        )

        serializer = HotelBookingSerializer(booking, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.AllowAny], url_path="initiate-payment")
    def initiate_payment(self, request, pk=None):
        """
        Transition a pending hotel booking to 'payment_initiated' and extend expiry by +20 minutes
        (capped at 45 minutes total from creation).
        """
        from datetime import timedelta
        booking = get_object_or_404(HotelBooking, id=pk)

        if booking.status not in [HotelBooking.BookingStatus.PENDING, HotelBooking.BookingStatus.PAYMENT_INITIATED]:
            return Response(
                {"error": f"Booking is '{booking.status}'. Cannot initiate payment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        extended_expiry = now + timedelta(minutes=20)
        max_expiry = (booking.created_at or now) + timedelta(minutes=45)
        booking.expires_at = min(extended_expiry, max_expiry)
        booking.status = HotelBooking.BookingStatus.PAYMENT_INITIATED
        booking.save(update_fields=["status", "expires_at"])

        return Response(
            {
                "message": "Payment initiated. Expiry extended.",
                "booking_id": str(booking.id),
                "status": booking.status,
                "expires_at": booking.expires_at.isoformat() if booking.expires_at else None,
            },
            status=status.HTTP_200_OK,
        )

    @decorators.action(
        detail=False, methods=["get", "post"], permission_classes=[permissions.AllowAny], url_path="check-availability"
    )
    def check_availability(self, request):
        """
        Check dynamic room inventory availability for a hotel room type and date range.
        Returns available status, available room count, and message.
        """
        data = request.data if request.method == "POST" else request.query_params
        hotel_id = data.get("hotel_id") or data.get("hotel")
        room_type_id = data.get("room_type_id") or data.get("room_type")
        check_in_str = data.get("check_in_date") or data.get("check_in")
        check_out_str = data.get("check_out_date") or data.get("check_out")
        rooms_requested = int(data.get("number_of_rooms") or data.get("rooms") or 1)

        if not room_type_id:
            return Response(
                {"available": False, "error": "room_type_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not check_in_str or not check_out_str:
            return Response(
                {"available": False, "error": "check_in_date and check_out_date are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from datetime import datetime
        from django.db.models import Sum, Value
        from django.db.models.functions import Coalesce

        try:
            if isinstance(check_in_str, str):
                check_in = datetime.strptime(check_in_str.split("T")[0], "%Y-%m-%d").date()
            else:
                check_in = check_in_str
            if isinstance(check_out_str, str):
                check_out = datetime.strptime(check_out_str.split("T")[0], "%Y-%m-%d").date()
            else:
                check_out = check_out_str
        except (ValueError, TypeError):
            return Response(
                {"available": False, "error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.now().date()
        if check_in < today:
            return Response(
                {"available": False, "error": "Check-in date cannot be in the past."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if check_in >= check_out or (check_out - check_in).days < 1:
            return Response(
                {"available": False, "error": "Minimum stay is 1 day. Check-out date must be strictly after check-in date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            room_type = HotelRoomType.objects.select_related("hotel").get(id=room_type_id, is_available=True)
        except HotelRoomType.DoesNotExist:
            return Response(
                {"available": False, "error": "Selected room type is not available for this hotel."},
                status=status.HTTP_404_NOT_FOUND,
            )

        ACTIVE_STATUSES = [
            HotelBooking.BookingStatus.PENDING,
            HotelBooking.BookingStatus.PAYMENT_INITIATED,
            HotelBooking.BookingStatus.CONFIRMED,
            HotelBooking.BookingStatus.CHECKED_IN,
        ]

        overlapping_rooms = HotelBooking.objects.filter(
            room_type=room_type,
            status__in=ACTIVE_STATUSES,
            check_in_date__lt=check_out,
            check_out_date__gt=check_in,
        ).aggregate(
            total=Coalesce(Sum("number_of_rooms"), Value(0))
        )["total"]

        available_rooms = max(0, room_type.total_rooms - overlapping_rooms)
        is_available = available_rooms >= rooms_requested

        # Duplicate reservation check for logged-in user or provided guest details
        user = request.user if request and request.user.is_authenticated else None
        guest_email = (data.get("guest_email") or data.get("email") or (user.email if user else "")).strip().lower()
        mobile_number = (data.get("mobile_number") or data.get("phone") or (user.phone if user else "")).strip()

        from django.db.models import Q
        dup_query = Q()
        if user:
            dup_query |= Q(user=user)
        if mobile_number:
            dup_query |= Q(guest_details__mobile_number=mobile_number)
        if guest_email:
            dup_query |= Q(guest_details__guest_email__iexact=guest_email)

        if dup_query:
            existing_booking = HotelBooking.objects.filter(
                dup_query,
                hotel=room_type.hotel,
                status__in=ACTIVE_STATUSES,
                check_in_date__lt=check_out,
                check_out_date__gt=check_in,
            ).first()

            if existing_booking:
                dup_msg = (
                    f"A booking already exists for this guest at {room_type.hotel.name} "
                    f"during the selected dates ({check_in} to {check_out}). "
                    f"You cannot have multiple active bookings at the same hotel for overlapping dates."
                )
                return Response(
                    {
                        "available": False,
                        "available_rooms": 0,
                        "requested_rooms": rooms_requested,
                        "room_type_id": str(room_type.id),
                        "room_type_name": room_type.name,
                        "hotel_id": str(room_type.hotel.id),
                        "hotel_name": room_type.hotel.name,
                        "error": dup_msg,
                        "message": dup_msg,
                    },
                    status=status.HTTP_200_OK,
                )

        if not is_available:
            sold_out_msg = (
                f"Sorry, suite '{room_type.name}' is sold out for {check_in} to {check_out}. "
                f"Only {available_rooms} room(s) available."
            )
            return Response(
                {
                    "available": False,
                    "available_rooms": available_rooms,
                    "requested_rooms": rooms_requested,
                    "room_type_id": str(room_type.id),
                    "room_type_name": room_type.name,
                    "hotel_id": str(room_type.hotel.id),
                    "hotel_name": room_type.hotel.name,
                    "error": sold_out_msg,
                    "message": sold_out_msg,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "available": True,
                "available_rooms": available_rooms,
                "requested_rooms": rooms_requested,
                "room_type_id": str(room_type.id),
                "room_type_name": room_type.name,
                "hotel_id": str(room_type.hotel.id),
                "hotel_name": room_type.hotel.name,
                "message": f"{available_rooms} room(s) available of type '{room_type.name}' for {check_in} to {check_out}.",
            },
            status=status.HTTP_200_OK,
        )
