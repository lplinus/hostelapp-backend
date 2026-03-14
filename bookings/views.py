from rest_framework import viewsets, permissions, decorators
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from .models import Booking
from .serializers import BookingSerializer


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.select_related("user", "hostel", "room_type").order_by(
        "-created_at"
    )
    serializer_class = BookingSerializer
    pagination_class = None
    # def perform_create(self, serializer):
    #     serializer.save(user=self.request.user)

    def perform_create(self, serializer):
        from .services.booking_email_service import BookingEmailService
        if self.request.user.is_authenticated:
            booking = serializer.save(user=self.request.user)
        else:
            booking = serializer.save()
        
        # Trigger confirmation email
        BookingEmailService.send_booking_confirmation(booking)


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
        if self.action in ["create", "send_otp", "verify_otp"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return super().get_queryset()

        from django.db.models import Q

        return super().get_queryset().filter(Q(user=user) | Q(hostel__owner=user))

    @decorators.action(
        detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated]
    )
    def owner(self, request):
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
        booking_id = request.data.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required"}, status=400)

        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found"}, status=404)

        if not request.user.is_staff and booking.hostel.owner != request.user:
            raise PermissionDenied("You do not have permission to check-in this booking.")

        if booking.status == "completed":
            return Response({"error": "Booking already checked in"}, status=400)

        if booking.status != "confirmed":
            return Response({"error": "Only confirmed bookings can be checked in"}, status=400)

        booking.status = "completed"
        booking.save()

        return Response({
            "message": "Check-in successful",
            "booking_id": booking.id
        })

    @decorators.action(
        detail=False, methods=["post"], permission_classes=[permissions.AllowAny]
    )
    def send_otp(self, request):
        phone = request.data.get("phone")
        if not phone:
            return Response({"error": "phone is required"}, status=400)
        
        from .services.booking_otp_service import BookingOTPService
        try:
            BookingOTPService.send_booking_otp(phone)
            return Response({"message": "OTP sent successfully"})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

    @decorators.action(
        detail=False, methods=["post"], permission_classes=[permissions.AllowAny]
    )
    def verify_otp(self, request):
        phone = request.data.get("phone")
        code = request.data.get("code")
        if not phone or not code:
            return Response({"error": "phone and code are required"}, status=400)
        
        from .services.booking_otp_service import BookingOTPService
        if BookingOTPService.verify_booking_otp(phone, code):
            return Response({"message": "Phone verified successfully"})
        else:
            return Response({"error": "Invalid or expired OTP"}, status=400)
