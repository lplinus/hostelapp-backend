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
        serializer.save(host=self.request.user)

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
        if self.action in ["create"]:
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
                "rental", "host", "user", "guest_details", "pricing_details", "cancellation_details"
            )
            .order_by("-created_at")
        )
        if user.is_staff:
            return qs
        if user.is_authenticated:
            # User can see bookings they made OR bookings for rentals they host
            return qs.filter(Q(user=user) | Q(host=user))
        return qs.none()

    def create(self, request, *args, **kwargs):
        serializer = VacationRentalBookingCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        response_serializer = VacationRentalBookingSerializer(booking, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="my-bookings")
    def my_bookings(self, request):
        """Returns the logged-in user's bookings as a guest."""
        bookings = self.get_queryset().filter(user=request.user)
        serializer = VacationRentalBookingSerializer(bookings, many=True, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="hosted-bookings")
    def hosted_bookings(self, request):
        """Returns reservation requests received by the host for their properties."""
        bookings = self.get_queryset().filter(host=request.user)
        serializer = VacationRentalBookingSerializer(bookings, many=True, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="approve")
    def approve(self, request, pk=None):
        """Host approves a pending reservation request and locks the calendar dates."""
        booking = get_object_or_404(VacationRentalBooking, id=pk)
        if booking.host != request.user and not request.user.is_staff:
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
        if booking.host != request.user and not request.user.is_staff:
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
