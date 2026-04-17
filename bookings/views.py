"""
Views for the Bookings application.
This module handles the creation, retrieval, and management of hostel bookings.
Includes support for guest bookings, OTP verification, and owner/staff dashboards.
"""

from rest_framework import viewsets, permissions, decorators, filters, status
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from .models import Booking
from .serializers import BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Booking model.
    Provides standard CRUD operations and custom actions for booking management.
    Supports filtering, searching, and ordering of booking records.
    """

    queryset = Booking.objects.select_related("user", "hostel", "room_type").order_by(
        "-created_at"
    )
    serializer_class = BookingSerializer
    pagination_class = None
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = {
        "check_in": ["gte", "lte", "exact"],
        "check_out": ["gte", "lte", "exact"],
        "created_at": ["gte", "lte", "exact"],
        "status": ["exact"],
        "booking_type": ["exact"],
    }
    search_fields = ["guest_name", "guest_email", "mobile_number", "hostel__name", "id"]
    ordering_fields = ["created_at", "check_in", "check_out", "total_price"]

    def create(self, request, *args, **kwargs):
        from .services.recaptcha_service import RecaptchaService

        RecaptchaService.verify(
            token=request.data.get("recaptcha_token"),
            action="booking",
        )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        from django.utils import timezone
        from datetime import timedelta
        # Default cooldown is 24 hours
        cooldown_time = timezone.now() + timedelta(hours=24)

        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user, cooldown_until=cooldown_time)
        else:
            serializer.save(cooldown_until=cooldown_time)

    def perform_update(self, serializer):
        obj = serializer.instance
        if not self.request.user.is_staff:
            if obj.user != self.request.user and obj.hostel.owner != self.request.user:
                raise PermissionDenied("You do not own this booking.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_staff:
            if (
                instance.user != self.request.user
                and instance.hostel.owner != self.request.user
            ):
                raise PermissionDenied("You do not own this booking.")
        instance.delete()

    def get_permissions(self):
        if self.action in [
            "create",
            "send_otp",
            "verify_otp",
            "confirm_pay_at_property",
        ]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return super().get_queryset()

        if self.action in ["confirm_pay_at_property"]:
            return super().get_queryset()

        if user.is_anonymous:
            return super().get_queryset().none()

        from django.db.models import Q

        return super().get_queryset().filter(Q(user=user) | Q(hostel__owner=user))

    @decorators.action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def owner(self, request):
        """
        Custom action to retrieve all bookings for hostels owned by the authenticated user.
        """
        bookings = (
            Booking.objects.filter(hostel__owner=request.user)
            .select_related("user", "hostel", "room_type")
            .order_by("-created_at")
        )
        serializer = self.get_serializer(bookings, many=True)
        return Response(serializer.data)

    @decorators.action(
        detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated]
    )
    def checkin(self, request):
        """
        Marks a booking as 'completed' (checked-in).
        Verification: Booking must be 'confirmed' and the user must be the hostel owner or staff.
        Accepts both full UUID and display-format IDs like 'STN-77D76716'.
        """
        booking_id = request.data.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required"}, status=400)

        booking_id = str(booking_id).strip()

        try:
            # If the booking_id is in display format (e.g. STN-77D76716),
            # strip the prefix and search by the first 8 hex chars of the UUID.
            if booking_id.upper().startswith("STN-"):
                short_hex = booking_id[4:].lower()  # e.g. "77d76716"
                booking = Booking.objects.get(id__startswith=short_hex)
            else:
                booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=404)
        except Exception:
            return Response({"error": "Invalid booking ID format"}, status=400)

        if not request.user.is_staff and booking.hostel.owner != request.user:
            raise PermissionDenied(
                "You do not have permission to check-in this booking."
            )

        if booking.status == "completed":
            return Response({"error": "Booking already checked in"}, status=400)

        if booking.status != "confirmed":
            return Response(
                {"error": "Only confirmed bookings can be checked in"}, status=400
            )

        booking.status = "completed"
        # Mark payment as paid for "pay at hostel" bookings upon check-in
        if booking.payment_method == "on_arrival":
            booking.payment_status = "paid"
        booking.save()

        return Response({"message": "Check-in successful", "booking_id": booking.id})

    @decorators.action(
        detail=False, methods=["post"], permission_classes=[permissions.AllowAny]
    )
    def send_otp(self, request):
        """
        Sends an OTP to the provided phone number for booking verification.
        Includes a 24-hour duplicate booking check and a smart OTP skip for previous users.
        """
        phone = request.data.get("phone")

        if not phone:
            return Response({"error": "phone is required"}, status=400)

        # 1. Booking Cooldown Check (Using the new cooldown_until column)
        from django.utils import timezone

        recent_booking = (
            Booking.objects.filter(mobile_number=phone)
            .order_by("-created_at")
            .first()
        )

        if (
            recent_booking
            and recent_booking.cooldown_until
            and recent_booking.cooldown_until > timezone.now()
            and recent_booking.status not in ["completed", "cancelled"]
        ):
            remaining_seconds = int(
                (recent_booking.cooldown_until - timezone.now()).total_seconds()
            )
            return Response(
                {
                    "error": "You have a pending or recent booking. Please wait 24 hours before booking another hostel.",
                    "is_cooldown": True,
                    "remaining_seconds": remaining_seconds,
                    "cooldown_until": recent_booking.cooldown_until,
                },
                status=400,
            )

        # 2. Smart OTP: Check if already verified via previous successful booking
        if Booking.objects.filter(
            mobile_number=phone, status__in=["confirmed", "completed"]
        ).exists():
            return Response(
                {
                    "message": "Phone number already verified via previous booking",
                    "verified": True,
                }
            )

        from .services.booking_otp_service import BookingOTPService

        try:
            BookingOTPService.send_booking_otp(phone)
            return Response({"message": "OTP sent successfully", "verified": False})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @decorators.action(
        detail=False, methods=["post"], permission_classes=[permissions.AllowAny]
    )
    def verify_otp(self, request):
        """
        Verifies the OTP sent to the user's phone.
        """
        phone = request.data.get("phone")
        code = request.data.get("code")
        if not phone or not code:
            return Response({"error": "phone and code are required"}, status=400)

        from .services.booking_otp_service import BookingOTPService

        if BookingOTPService.verify_booking_otp(phone, code):
            return Response({"message": "Phone verified successfully"})
        else:
            return Response({"error": "Invalid or expired OTP"}, status=400)

    @decorators.action(
        detail=True, methods=["post"], permission_classes=[permissions.AllowAny]
    )
    def confirm_pay_at_property(self, request, pk=None):
        """
        Confirms a pending booking with the 'pay at property' option.
        Updates status to 'confirmed' and sends a confirmation email.
        """
        booking = self.get_object()

        if booking.status != "pending":
            return Response(
                {"error": "Only pending bookings can be confirmed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.payment_method = "on_arrival"
        booking.payment_status = "pending"
        booking.status = "confirmed"
        booking.save()

        # Send confirmation email
        from .services.booking_email_service import BookingEmailService

        try:
            BookingEmailService.send_booking_confirmation(booking)
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to send email: {e}")

        return Response(
            {
                "message": "Booking confirmed with Pay at Property option.",
                "booking_id": booking.id,
            }
        )
