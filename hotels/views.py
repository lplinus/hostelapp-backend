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
        serializer = HotelRoomTypeSerializer(data={**request.data, "hotel": hotel.id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="upload-images")
    def upload_images(self, request, slug=None):
        """Uploads multiple hotel photos via multipart form data."""
        hotel = self.get_object()
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

    def perform_destroy(self, instance):
        instance.delete()

    def create(self, request, *args, **kwargs):
        hotel_id = request.data.get("hotel")
        if not hotel_id:
            return Response({"detail": "hotel id is required."}, status=status.HTTP_400_BAD_REQUEST)

        hotel = get_object_or_404(Hotel, id=hotel_id)
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
            if booking.payment_details.payment_method == HotelPayment.PaymentMethod.PAY_AT_HOTEL:
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
