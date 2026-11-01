from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, permissions, decorators, status, filters
from rest_framework.response import Response
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
        serializer.save(is_active=True, is_approved=True)

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

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="my-hotels")
    def my_hotels(self, request):
        """Returns hotels for dashboard property management."""
        hotels = self.get_queryset()
        serializer = HotelSerializer(hotels, many=True, context={"request": request})
        return Response(serializer.data)

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
    - Guests can create bookings atomically.
    - Users can view their own bookings.
    - Users/Admins can cancel reservations.
    """
    queryset = (
        HotelBooking.objects.select_related("hotel", "room_type", "user", "guest_details", "payment_details", "cancellation_details")
        .order_by("-created_at")
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "status": ["exact"],
        "check_in_date": ["gte", "lte", "exact"],
        "check_out_date": ["gte", "lte", "exact"],
        "hotel": ["exact"],
    }
    search_fields = ["booking_reference", "hotel__name", "guest_details__guest_name", "guest_details__mobile_number"]
    ordering_fields = ["created_at", "check_in_date", "total_amount"]

    def get_permissions(self):
        if self.action in ["create"]:
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
                "hotel", "room_type", "user", "guest_details", "payment_details", "cancellation_details"
            )
            .order_by("-created_at")
        )
        if user.is_staff:
            return qs
        if user.is_authenticated:
            return qs.filter(user=user)
        return qs.none()

    def create(self, request, *args, **kwargs):
        serializer = HotelBookingCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        response_serializer = HotelBookingSerializer(booking, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="my-bookings")
    def my_bookings(self, request):
        """Returns the authenticated user's hotel reservation history."""
        bookings = self.get_queryset().filter(user=request.user)
        serializer = HotelBookingSerializer(bookings, many=True, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancels a booking and restores room inventory."""
        booking = get_object_or_404(HotelBooking, id=pk)
        if not request.user.is_staff and booking.user != request.user:
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
