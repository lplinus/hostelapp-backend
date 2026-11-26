import logging
from Hbackend.throttles import BookingOTPThrottle
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.db.models import Q, Exists, OuterRef
from rest_framework import viewsets, permissions, decorators, status, filters
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError

from adsense.models import AdCampaign
from adsense.services import get_active_banner_property_ids
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
from .filters import VacationRentalFilter
from Hbackend.pagination import TenResultsSetPagination

logger = logging.getLogger(__name__)


def _ensure_rental_host(user, rental):
    """Only the rental's host (or staff) may modify the rental, its images and calendar."""
    if not user.is_staff and getattr(rental, "host_id", None) != user.id:
        raise PermissionDenied("You do not own this vacation rental.")


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
    serializer_class = VacationRentalSerializer
    pagination_class = TenResultsSetPagination
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = VacationRentalFilter
    search_fields = ["title", "city__name", "area__name", "address", "tagline"]
    ordering_fields = ["price_per_night", "rating_avg", "created_at"]
    ordering = ["-is_featured", "-rating_avg"]

    def get_queryset(self):
        now = timezone.now()
        active_sponsored = AdCampaign.objects.filter(
            vacation_rental=OuterRef("pk"),
            status=AdCampaign.CampaignStatus.ACTIVE,
            is_deleted=0,
            start_date__lte=now,
            end_date__gte=now,
        )
        qs = (
            VacationRental.objects.select_related("city", "area", "host")
            .prefetch_related("amenities", "images")
            .annotate(is_sponsored=Exists(active_sponsored))
            .all()
        )
        if self.action in ["list", "retrieve"]:
            qs = qs.filter(is_active=True, is_approved=True)
            # Mutual Exclusion: Exclude properties currently featured in the active Ad Banner
            if self.action == "list":
                city = (
                    self.request.query_params.get("city")
                    or self.request.query_params.get("search")
                    or self.request.query_params.get("q")
                    or ""
                ).strip()
                city_id = self.request.query_params.get("city_id")
                city_slug = self.request.query_params.get("city_slug")
                search_id = self.request.query_params.get("search_id") or self.request.query_params.get("banner_seed")
                banner_vr_ids = get_active_banner_property_ids(
                    property_type="vacation_rental",
                    city=city,
                    city_slug=city_slug,
                    city_id=city_id,
                    search_id=search_id,
                )
                if banner_vr_ids:
                    qs = qs.exclude(id__in=banner_vr_ids)
            return qs
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

    def perform_update(self, serializer):
        _ensure_rental_host(self.request.user, serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        _ensure_rental_host(self.request.user, instance)
        instance.delete()

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

    def perform_create(self, serializer):
        _ensure_rental_host(self.request.user, serializer.validated_data.get("rental"))
        serializer.save()

    def perform_update(self, serializer):
        _ensure_rental_host(self.request.user, serializer.instance.rental)
        serializer.save()

    def perform_destroy(self, instance):
        _ensure_rental_host(self.request.user, instance.rental)
        instance.delete()


class VacationRentalImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing vacation rental images (upload, list, and delete).
    """
    queryset = VacationRentalImage.objects.select_related("rental").all()
    serializer_class = VacationRentalImageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["rental", "space"]

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def perform_update(self, serializer):
        _ensure_rental_host(self.request.user, serializer.instance.rental)
        serializer.save()

    def perform_destroy(self, instance):
        _ensure_rental_host(self.request.user, instance.rental)
        instance.delete()

    def create(self, request, *args, **kwargs):
        rental_id = request.data.get("rental")
        if not rental_id:
            return Response({"detail": "rental id is required."}, status=status.HTTP_400_BAD_REQUEST)

        rental = get_object_or_404(VacationRental, id=rental_id)
        _ensure_rental_host(request.user, rental)

        space = request.data.get("space") or VacationRentalImage.SpaceType.OTHER
        if space not in VacationRentalImage.SpaceType.values:
            space = VacationRentalImage.SpaceType.OTHER

        # Direct-to-cloud registration path (browser already uploaded to ImageKit/Cloudinary)
        raw_urls = request.data.get("image_urls")
        if isinstance(raw_urls, list) and len(raw_urls) > 0:
            clean_urls = [u for u in raw_urls if isinstance(u, str) and u.startswith(("https://", "http://"))]
            if not clean_urls:
                return Response({"detail": "Valid image_urls are required."}, status=status.HTTP_400_BAD_REQUEST)
            from django.core.exceptions import ValidationError as DjangoValidationError
            from cms.models import StorageSettings
            try:
                VacationRentalImage.validate_upload_quota(rental, space=space, incoming_count=len(clean_urls))
            except DjangoValidationError as exc:
                return Response({"detail": exc.messages[0] if getattr(exc, "messages", None) else str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            provider = request.data.get("provider") or StorageSettings.get_active_provider()
            existing_count = rental.images.count()
            created = []
            for idx, url in enumerate(clean_urls):
                img = VacationRentalImage.objects.create(
                    rental=rental,
                    image=url,
                    provider=provider,
                    space=space,
                    caption=f"{rental.title} Photo {existing_count + idx + 1}",
                    order=existing_count + idx,
                    is_primary=(existing_count == 0 and idx == 0),
                )
                created.append(VacationRentalImageSerializer(img, context={"request": request}).data)
            return Response(created, status=status.HTTP_201_CREATED)

        image_files = []
        for key in ["images", "images[]", "image"]:
            if key in request.FILES:
                image_files.extend(request.FILES.getlist(key))
        for key in sorted(request.FILES.keys()):
            if key not in ["images", "images[]", "image"] and ("image" in key.lower() or "photo" in key.lower() or "file" in key.lower()):
                image_files.extend(request.FILES.getlist(key))

        if not image_files:
            return Response({"detail": "No image files provided."}, status=status.HTTP_400_BAD_REQUEST)

        from django.core.exceptions import ValidationError as DjangoValidationError
        from Hbackend.utils import validate_image_size
        from hostels.services import ImageUploadService
        import os

        space = request.data.get("space") or VacationRentalImage.SpaceType.OTHER
        if space not in VacationRentalImage.SpaceType.values:
            space = VacationRentalImage.SpaceType.OTHER

        try:
            for file_obj in image_files:
                validate_image_size(file_obj)
            VacationRentalImage.validate_upload_quota(rental, space=space, incoming_count=len(image_files))
        except DjangoValidationError as exc:
            return Response({"detail": exc.messages[0] if getattr(exc, "messages", None) else str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        existing_count = rental.images.count()
        rental_slug = rental.slug or f"rental-{rental.id}"
        batch_items = [
            (
                file_obj,
                f"{rental_slug}-{space}-{existing_count + idx + 1}{os.path.splitext(getattr(file_obj, 'name', 'image'))[1] or '.webp'}",
            )
            for idx, file_obj in enumerate(image_files)
        ]
        uploaded_results = ImageUploadService().upload_images_batch(
            batch_items,
            folder=f"vacation_rentals/{rental_slug}",
        )

        created = []
        for idx, res in enumerate(uploaded_results):
            img = VacationRentalImage.objects.create(
                rental=rental,
                image=res["url"],
                provider=res["provider"],
                space=space,
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
            "check_availability",
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

    # Direct PUT/PATCH/DELETE on a booking is limited to the host/owner or staff.
    # Guests change their bookings through the dedicated actions (e.g. cancel).
    def _ensure_booking_manager(self, booking):
        user = self.request.user
        if (
            user.is_staff
            or booking.host_id == user.id
            or booking.owner_id == user.id
            or booking.rental.host_id == user.id
        ):
            return
        raise PermissionDenied("You do not have permission to modify this booking.")

    def perform_update(self, serializer):
        self._ensure_booking_manager(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._ensure_booking_manager(instance)
        instance.delete()

    def create(self, request, *args, **kwargs):
        serializer = VacationRentalBookingCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()

        # Offload vacation rental booking flow, date locking, notifications, and QR generation to Celery
        from django.db import transaction
        from .tasks import process_vacation_rental_booking_task

        transaction.on_commit(
            lambda: process_vacation_rental_booking_task.delay(str(booking.id))
        )

        response_serializer = VacationRentalBookingSerializer(booking, context={"request": request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    # ── OTP Verification Actions (mirroring working hostel pipeline) ───────────────

    @decorators.action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny], url_path="send_otp", throttle_classes=[BookingOTPThrottle])
    def send_otp(self, request):
        """Sends an OTP to the phone number for vacation rental booking verification."""
        phone = request.data.get("phone") or request.data.get("mobile_number")
        if not phone:
            return Response({"error": "phone is required"}, status=status.HTTP_400_BAD_REQUEST)

        from bookings.services.booking_otp_service import BookingOTPService
        try:
            BookingOTPService.send_booking_otp(phone)
            return Response({"message": "OTP sent successfully", "verified": False})
        except Exception:
            # Log the real error for developers; never send internal details to the browser.
            logger.exception("Booking OTP send failed")
            return Response(
                {"error": "Could not send the verification code. Please try again in a moment."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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

    @decorators.action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny], url_path="send_email_otp", throttle_classes=[BookingOTPThrottle])
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
        except Exception:
            # Log the real error for developers; never send internal details to the browser.
            logger.exception("Booking OTP send failed")
            return Response(
                {"error": "Could not send the verification code. Please try again in a moment."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
        from django.db.models import Q
        qs = self.get_queryset()
        status_param = request.query_params.get("status")
        if status_param and status_param != "all":
            qs = qs.filter(status=status_param)
        search_param = request.query_params.get("search")
        if search_param:
            search_param = search_param.strip()
            qs = qs.filter(
                Q(booking_reference__icontains=search_param)
                | Q(rental__title__icontains=search_param)
                | Q(guest_details__guest_name__icontains=search_param)
            )
        serializer = VacationRentalBookingSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="hosted-bookings")
    def hosted_bookings(self, request):
        """Returns reservation requests received by the host for their properties."""
        from django.db.models import Q
        user = request.user
        qs = self.get_queryset().filter(Q(host=user) | Q(owner=user) | Q(rental__host=user))
        status_param = request.query_params.get("status")
        if status_param and status_param != "all":
            qs = qs.filter(status=status_param)
        search_param = request.query_params.get("search")
        if search_param:
            search_param = search_param.strip()
            qs = qs.filter(
                Q(booking_reference__icontains=search_param)
                | Q(rental__title__icontains=search_param)
                | Q(guest_details__guest_name__icontains=search_param)
            )
        serializer = VacationRentalBookingSerializer(qs, many=True, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=False, methods=["get"], permission_classes=[permissions.IsAuthenticated], url_path="owner")
    def owner(self, request):
        """Mirrors /api/bookings/owner/ so vacation rental bookings can be queried identically."""
        return self.hosted_bookings(request)

    @decorators.action(detail=False, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="checkin")
    def checkin(self, request):
        """Marks a CONFIRMED vacation rental reservation as checked-in, only during the stay dates."""
        from django.db import transaction
        from Hbackend.booking_policies import check_in_window_error

        booking_id = request.data.get("booking_id")
        if not booking_id:
            return Response({"error": "booking_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        booking_id_str = str(booking_id).strip()
        lookup = (
            {"booking_reference": booking_id_str.upper()}
            if booking_id_str.upper().startswith("VRB-")
            else {"id": booking_id_str}
        )

        with transaction.atomic():
            try:
                booking = VacationRentalBooking.objects.select_for_update().select_related("rental").get(**lookup)
            except (VacationRentalBooking.DoesNotExist, ValueError, DjangoValidationError):
                return Response({"error": "Vacation rental booking not found"}, status=status.HTTP_404_NOT_FOUND)

            if (
                not request.user.is_staff
                and booking.host_id != request.user.id
                and getattr(booking, "owner_id", None) != request.user.id
                and getattr(booking.rental, "host_id", None) != request.user.id
            ):
                raise PermissionDenied("You do not have permission to check-in this vacation rental booking.")

            if booking.status == VacationRentalBooking.BookingStatus.CHECKED_IN:
                return Response({"error": "Booking already checked in"}, status=status.HTTP_400_BAD_REQUEST)
            if booking.status != VacationRentalBooking.BookingStatus.CONFIRMED:
                return Response(
                    {"error": f"Only confirmed bookings can be checked in. This booking is '{booking.get_status_display()}'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            window_error = check_in_window_error(booking.check_in_date, booking.check_out_date)
            if window_error:
                return Response({"error": window_error}, status=status.HTTP_400_BAD_REQUEST)

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

        # Offload confirmation notifications and QR generation asynchronously via Celery
        from django.db import transaction
        from .tasks import send_vacation_rental_confirmation_task

        transaction.on_commit(
            lambda: send_vacation_rental_confirmation_task.delay(str(booking.id))
        )

        serializer = VacationRentalBookingSerializer(booking, context={"request": request})
        return Response(serializer.data)

    @decorators.action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated], url_path="initiate-payment")
    def initiate_payment(self, request, pk=None):
        """
        Transition a pending vacation rental booking to 'payment_initiated' and extend expiry by +20 minutes
        (capped at 45 minutes total from creation).
        """
        booking = get_object_or_404(VacationRentalBooking, id=pk)

        # Only the guest who made the booking (or staff) can move it into payment.
        if not request.user.is_staff and booking.user_id != request.user.id:
            return Response({"detail": "You do not own this booking."}, status=status.HTTP_403_FORBIDDEN)

        if booking.status not in [
            VacationRentalBooking.BookingStatus.PENDING_APPROVAL,
            VacationRentalBooking.BookingStatus.PAYMENT_INITIATED,
        ]:
            return Response(
                {"error": f"Booking is '{booking.status}'. Cannot initiate payment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        extended_expiry = now + timedelta(minutes=20)
        max_expiry = (booking.created_at or now) + timedelta(minutes=45)
        booking.expires_at = min(extended_expiry, max_expiry)
        booking.status = VacationRentalBooking.BookingStatus.PAYMENT_INITIATED
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
        """Cancels a reservation that has not started yet, frees the calendar and records the policy-based refund."""
        from django.db import transaction
        from Hbackend.booking_policies import calculate_refund

        CANCELLABLE = [
            VacationRentalBooking.BookingStatus.PENDING_APPROVAL,
            VacationRentalBooking.BookingStatus.PAYMENT_INITIATED,
            VacationRentalBooking.BookingStatus.CONFIRMED,
        ]

        with transaction.atomic():
            booking = get_object_or_404(
                VacationRentalBooking.objects.select_for_update().select_related("rental"), id=pk
            )
            user = request.user
            is_guest = booking.user_id is not None and booking.user_id == user.id
            is_host = (
                booking.host_id == user.id
                or getattr(booking, "owner_id", None) == user.id
                or getattr(booking.rental, "host_id", None) == user.id
            )
            if not is_guest and not is_host and not user.is_staff:
                return Response({"detail": "You do not have permission to cancel this booking."}, status=status.HTTP_403_FORBIDDEN)

            if booking.status == VacationRentalBooking.BookingStatus.CANCELLED:
                return Response({"detail": "This booking is already cancelled."}, status=status.HTTP_400_BAD_REQUEST)
            if booking.status not in CANCELLABLE:
                return Response(
                    {"detail": f"A booking that is '{booking.get_status_display()}' can no longer be cancelled."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            reason = request.data.get("reason") or "Cancelled by user"
            if is_guest:
                cancelled_by = VacationRentalCancellation.CancelledBy.GUEST
            elif is_host:
                cancelled_by = VacationRentalCancellation.CancelledBy.HOST
            else:
                cancelled_by = VacationRentalCancellation.CancelledBy.ADMIN

            pricing = getattr(booking, "pricing_details", None)
            paid_amount = pricing.total_price if pricing and pricing.payment_status == "paid" else 0
            policy = booking.rental.cancellation_policy
            refund_amount = calculate_refund(
                "rental_moderate" if policy == "moderate" else policy,
                paid_amount,
                booking.check_in_date,
                cancelled_by_property=not is_guest,
            )

            booking.status = VacationRentalBooking.BookingStatus.CANCELLED
            booking.save(update_fields=["status"])

            # Free the calendar dates
            VacationRentalAvailability.objects.filter(
                rental=booking.rental,
                date__gte=booking.check_in_date,
                date__lt=booking.check_out_date,
                reason=VacationRentalAvailability.BlockReason.BOOKED,
            ).delete()

            VacationRentalCancellation.objects.create(
                booking=booking,
                cancellation_policy_applied=policy,
                cancelled_by=cancelled_by,
                reason=reason,
                refund_amount=refund_amount,
                refund_status=VacationRentalCancellation.RefundStatus.PENDING,
            )

        serializer = VacationRentalBookingSerializer(booking, context={"request": request})
        return Response(serializer.data)

    @decorators.action(
        detail=False, methods=["get", "post"], permission_classes=[permissions.AllowAny], url_path="check-availability"
    )
    def check_availability(self, request):
        """
        Check whole-property availability for a vacation rental over a date range.
        Considers both active bookings and host calendar blocks.
        """
        data = request.data if request.method == "POST" else request.query_params
        rental_id = data.get("rental_id") or data.get("rental")
        check_in_str = data.get("check_in_date") or data.get("check_in")
        check_out_str = data.get("check_out_date") or data.get("check_out")

        if not rental_id:
            return Response(
                {"available": False, "error": "rental_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not check_in_str or not check_out_str:
            return Response(
                {"available": False, "error": "check_in_date and check_out_date are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from datetime import datetime

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
            rental = VacationRental.objects.get(id=rental_id, is_active=True)
        except VacationRental.DoesNotExist:
            return Response(
                {"available": False, "error": "Vacation rental does not exist or is inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 1. Overlapping bookings
        overlap_booking = (
            VacationRentalBooking.objects.filter(rental=rental)
            .filter(check_in_date__lt=check_out, check_out_date__gt=check_in)
            .exclude(status__in=[VacationRentalBooking.BookingStatus.CANCELLED, VacationRentalBooking.BookingStatus.DECLINED])
        )
        if overlap_booking.exists():
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

            if dup_query and overlap_booking.filter(dup_query).exists():
                dup_msg = (
                    f"A booking already exists for this guest at '{rental.title}' "
                    f"during the selected dates ({check_in} to {check_out}). "
                    f"You cannot have multiple active bookings at the same property for overlapping dates."
                )
                return Response(
                    {
                        "available": False,
                        "rental_id": str(rental.id),
                        "rental_title": rental.title,
                        "error": dup_msg,
                        "message": dup_msg,
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {
                    "available": False,
                    "rental_id": str(rental.id),
                    "rental_title": rental.title,
                    "message": "These dates are already booked. Please choose different dates.",
                },
                status=status.HTTP_200_OK,
            )

        # 2. Blocked dates
        blocked_dates = VacationRentalAvailability.objects.filter(
            rental=rental,
            date__gte=check_in,
            date__lt=check_out,
            is_available=False,
        )
        if blocked_dates.exists():
            return Response(
                {
                    "available": False,
                    "rental_id": str(rental.id),
                    "rental_title": rental.title,
                    "message": "One or more selected dates are blocked on the host calendar.",
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "available": True,
                "rental_id": str(rental.id),
                "rental_title": rental.title,
                "hold_minutes": 8,
                "hold_seconds": 480,
                "message": f"'{rental.title}' is available from {check_in} to {check_out}!",
            },
            status=status.HTTP_200_OK,
        )

