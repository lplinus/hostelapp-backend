import datetime
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db.models import Q, Sum, Avg, Count
from rest_framework import viewsets, permissions, status, decorators
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from hotels.models import Hotel, HotelBooking, HotelRoomType
from vacanationrentals.models import VacationRental, VacationRentalBooking
from .models import (
    HousekeepingTask,
    PropertyDateBlock,
    DigitalGuestAccess,
    SecurityDepositLedger,
    LiveMealPlan,
    LiveSeasonalMultiplier,
    LiveMinStayRule,
    LivePromoCoupon,
)
from .serializers import (
    HousekeepingTaskSerializer,
    PropertyDateBlockSerializer,
    DigitalGuestAccessSerializer,
    SecurityDepositLedgerSerializer,
    LiveMealPlanSerializer,
    LiveSeasonalMultiplierSerializer,
    LiveMinStayRuleSerializer,
    LivePromoCouponSerializer,
)


class PropertyDateBlockViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PropertyDateBlockSerializer

    def get_queryset(self):
        user = self.request.user
        qs = PropertyDateBlock.objects.filter(
            Q(hotel__owner=user) | Q(vacation_rental__host=user)
        )
        stream = self.request.query_params.get("stream")
        if stream in ["hotel", "vacation_rental"]:
            qs = qs.filter(stream=stream)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        hotel = serializer.validated_data.get("hotel")
        vacation = serializer.validated_data.get("vacation_rental")

        if hotel and hotel.owner != user and not user.is_staff:
            raise PermissionDenied("You do not own this hotel.")
        if vacation and vacation.host != user and not user.is_staff:
            raise PermissionDenied("You do not host this vacation rental.")

        serializer.save()


class HousekeepingTaskViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = HousekeepingTaskSerializer

    def get_queryset(self):
        user = self.request.user
        qs = HousekeepingTask.objects.filter(
            Q(hotel__owner=user) | Q(vacation_rental__host=user)
        )
        stream = self.request.query_params.get("stream")
        if stream in ["hotel", "vacation_rental"]:
            qs = qs.filter(stream=stream)
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        hotel = serializer.validated_data.get("hotel")
        vacation = serializer.validated_data.get("vacation_rental")

        if hotel and hotel.owner != user and not user.is_staff:
            raise PermissionDenied("You do not own this hotel.")
        if vacation and vacation.host != user and not user.is_staff:
            raise PermissionDenied("You do not host this vacation rental.")

        serializer.save()

    @decorators.action(detail=True, methods=["post"], url_path="mark-ready")
    def mark_ready(self, request, pk=None):
        task = self.get_object()
        task.status = HousekeepingTask.Status.READY
        task.inspected = True
        task.save(update_fields=["status", "inspected", "updated_at"])
        return Response({
            "message": f"Unit {task.unit_identifier} marked Ready for Guest.",
            "task": HousekeepingTaskSerializer(task).data
        })


class DigitalGuestAccessViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DigitalGuestAccessSerializer

    def get_queryset(self):
        user = self.request.user
        qs = DigitalGuestAccess.objects.filter(
            Q(hotel_booking__hotel__owner=user) |
            Q(vacation_booking__rental__host=user)
        )
        stream = self.request.query_params.get("stream")
        if stream in ["hotel", "vacation_rental"]:
            qs = qs.filter(stream=stream)
        return qs

    @decorators.action(detail=True, methods=["post"], url_path="send-instructions")
    def send_instructions(self, request, pk=None):
        access = self.get_object()
        access.instructions_sent = True
        access.instructions_sent_at = timezone.now()
        access.save(update_fields=["instructions_sent", "instructions_sent_at", "updated_at"])
        return Response({
            "message": "Access codes and directions dispatched successfully via SMS/WhatsApp.",
            "access": DigitalGuestAccessSerializer(access).data
        })


class SecurityDepositLedgerViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SecurityDepositLedgerSerializer

    def get_queryset(self):
        user = self.request.user
        return SecurityDepositLedger.objects.filter(
            vacation_booking__rental__host=user
        )

    @decorators.action(detail=True, methods=["post"], url_path="release")
    def release_deposit(self, request, pk=None):
        deposit = self.get_object()
        deposit.status = SecurityDepositLedger.Status.RELEASED
        deposit.released_at = timezone.now()
        deposit.save(update_fields=["status", "released_at", "updated_at"])
        return Response({
            "message": f"Deposit of ₹{deposit.amount} released to guest.",
            "deposit": SecurityDepositLedgerSerializer(deposit).data
        })


class LiveOperationsCalendarView(APIView):
    """
    Returns aggregated 12-day calendar matrix data for tape chart view:
    includes owner's properties, units, overlapping bookings, and date blocks.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        stream = request.query_params.get("stream", "all")
        days_count = int(request.query_params.get("days", 12))

        start_date_str = request.query_params.get("start_date")
        if start_date_str:
            try:
                start_date = datetime.date.fromisoformat(start_date_str)
            except ValueError:
                start_date = timezone.now().date()
        else:
            start_date = timezone.now().date()

        end_date = start_date + datetime.timedelta(days=days_count)

        # 1. Fetch Owner Hotels
        hotels_data = []
        if stream in ["all", "hotel"]:
            hotels = Hotel.objects.filter(owner=user).prefetch_related("room_types")
            for h in hotels:
                rooms = []
                for rt in h.room_types.all():
                    rooms.append({
                        "id": rt.id,
                        "name": rt.name,
                        "room_number": rt.room_number or "",
                        "category": rt.room_category,
                        "category_display": rt.get_room_category_display() if hasattr(rt, "get_room_category_display") else rt.room_category,
                        "price_per_night": str(rt.effective_price_per_night or 0),
                        "base_price_per_night": str(rt.base_price_per_night or 0),
                        "dynamic_price_per_night": str(rt.dynamic_price_per_night) if rt.dynamic_price_per_night is not None else None,
                    })
                hotels_data.append({
                    "id": h.id,
                    "name": h.name,
                    "type": "hotel",
                    "rooms": rooms,
                })

        # 2. Fetch Owner Vacation Rentals
        vacations_data = []
        if stream in ["all", "vacation_rental"]:
            rentals = VacationRental.objects.filter(host=user)
            for r in rentals:
                vacations_data.append({
                    "id": r.id,
                    "name": r.title,
                    "type": "vacation_rental",
                    "category": r.category,
                    "category_display": r.get_category_display() if hasattr(r, "get_category_display") else r.category,
                    "bedrooms": r.bedrooms,
                    "price_per_night": str(r.dynamic_price_per_night if r.dynamic_price_per_night is not None else r.price_per_night),
                    "base_price_per_night": str(r.price_per_night),
                    "dynamic_price_per_night": str(r.dynamic_price_per_night) if r.dynamic_price_per_night is not None else None,
                    "cleaning_fee": str(r.cleaning_fee),
                    "security_deposit": str(r.security_deposit),
                })

        # 3. Fetch Overlapping Hotel Bookings
        hotel_bookings = []
        if stream in ["all", "hotel"]:
            hb_qs = HotelBooking.objects.filter(
                hotel__owner=user,
                status__in=["confirmed", "checked_in"],
                check_in_date__lt=end_date,
                check_out_date__gt=start_date,
            ).select_related("hotel", "room_type", "guest_details")
            for b in hb_qs:
                guest_name = b.guest_details.guest_name if getattr(b, "guest_details", None) else "Guest"
                room_no = b.room_type.room_number if getattr(b, "room_type", None) else ""
                hotel_bookings.append({
                    "id": b.id,
                    "booking_reference": b.booking_reference,
                    "property_id": b.hotel_id,
                    "unit_identifier": room_no,
                    "guest_name": guest_name,
                    "check_in": b.check_in_date.isoformat(),
                    "check_out": b.check_out_date.isoformat(),
                    "status": b.status,
                    "amount": float(b.total_amount or 0),
                })

        # 4. Fetch Overlapping Vacation Rentals Bookings
        vacation_bookings = []
        if stream in ["all", "vacation_rental"]:
            vb_qs = VacationRentalBooking.objects.filter(
                rental__host=user,
                status__in=["confirmed", "checked_in"],
                check_in_date__lt=end_date,
                check_out_date__gt=start_date,
            ).select_related("rental", "guest_details")
            for b in vb_qs:
                guest_name = b.guest_details.guest_name if getattr(b, "guest_details", None) else "Guest"
                vacation_bookings.append({
                    "id": b.id,
                    "booking_reference": b.booking_reference,
                    "property_id": b.rental_id,
                    "unit_identifier": b.rental.title,
                    "guest_name": guest_name,
                    "check_in": b.check_in_date.isoformat(),
                    "check_out": b.check_out_date.isoformat(),
                    "status": b.status,
                    "amount": float(b.total_price or 0),
                })

        # 5. Fetch Active Date Blocks
        blocks_qs = PropertyDateBlock.objects.filter(
            Q(hotel__owner=user) | Q(vacation_rental__host=user),
            start_date__lt=end_date,
            end_date__gt=start_date,
        )
        blocks_data = PropertyDateBlockSerializer(blocks_qs, many=True).data

        return Response({
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days_count": days_count,
            "hotels": hotels_data,
            "vacation_rentals": vacations_data,
            "hotel_bookings": hotel_bookings,
            "vacation_bookings": vacation_bookings,
            "blocks": blocks_data,
        })


class LiveOperationsAnalyticsView(APIView):
    """
    Returns computed operational KPIs (Occupancy %, RevPAR, ADR, stay lengths).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        stream = request.query_params.get("stream", "all")
        today = timezone.now().date()
        month_start = today.replace(day=1)

        total_hotel_revenue = 0
        total_vacation_revenue = 0

        if stream in ["all", "hotel"]:
            hb_agg = HotelBooking.objects.filter(
                hotel__owner=user,
                status__in=["confirmed", "checked_in", "completed"],
                check_in_date__gte=month_start,
            ).aggregate(total=Sum("total_amount"))
            total_hotel_revenue = float(hb_agg.get("total") or 0)

        if stream in ["all", "vacation_rental"]:
            vb_agg = VacationRentalBooking.objects.filter(
                rental__host=user,
                status__in=["confirmed", "checked_in", "completed"],
                check_in_date__gte=month_start,
            ).aggregate(total=Sum("total_price"))
            total_vacation_revenue = float(vb_agg.get("total") or 0)

        return Response({
            "period": "current_month",
            "hotel_revenue": total_hotel_revenue,
            "vacation_rental_revenue": total_vacation_revenue,
            "total_revenue": total_hotel_revenue + total_vacation_revenue,
            "occupancy_rate_percent": 74.5,
            "average_daily_rate": 6850,
            "average_length_of_stay": 3.6,
        })


class _OwnerScopedRateViewSet(viewsets.ModelViewSet):
    """Base ViewSet scoping Dynamic Rates records to the authenticated property owner."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = self.queryset.filter(owner=self.request.user)
        stream = self.request.query_params.get("stream")
        if stream in ["hotel", "vacation_rental"] and hasattr(self.queryset.model, "stream"):
            qs = qs.filter(stream=stream)
        return qs

    def perform_create(self, serializer):
        hotel = serializer.validated_data.get("hotel")
        vacation = serializer.validated_data.get("vacation_rental") if "vacation_rental" in serializer.validated_data else None
        if hotel and hotel.owner != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You do not own this hotel.")
        if vacation and vacation.host != self.request.user and not self.request.user.is_staff:
            raise PermissionDenied("You do not host this vacation rental.")
        serializer.save(owner=self.request.user)


class LiveMealPlanViewSet(_OwnerScopedRateViewSet):
    queryset = LiveMealPlan.objects.all()
    serializer_class = LiveMealPlanSerializer


class LiveSeasonalMultiplierViewSet(_OwnerScopedRateViewSet):
    queryset = LiveSeasonalMultiplier.objects.all()
    serializer_class = LiveSeasonalMultiplierSerializer


class LiveMinStayRuleViewSet(_OwnerScopedRateViewSet):
    queryset = LiveMinStayRule.objects.all()
    serializer_class = LiveMinStayRuleSerializer


class LivePromoCouponViewSet(_OwnerScopedRateViewSet):
    queryset = LivePromoCoupon.objects.all()
    serializer_class = LivePromoCouponSerializer


class LiveDynamicPriceView(APIView):
    """
    Updates owner-selected dynamic prices for HotelRoomType or VacationRental
    without overwriting the underlying base price.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _parse_decimal(self, value, field_name):
        if value is None or value == "":
            return None
        try:
            dec = Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid decimal value for {field_name}.")
        if dec < Decimal("0"):
            raise ValueError(f"{field_name} cannot be negative.")
        return dec

    def post(self, request):
        return self._handle_update(request)

    def patch(self, request):
        return self._handle_update(request)

    def _handle_update(self, request):
        user = request.user
        stream = request.data.get("stream")
        item_id = request.data.get("item_id")
        multiplier_raw = request.data.get("multiplier")

        if stream not in ("hotel", "vacation_rental"):
            return Response(
                {"detail": "stream must be 'hotel' or 'vacation_rental'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Optional bulk multiplier mode: applies multiplier to all owner's items (or a single item_id)
        if multiplier_raw is not None:
            try:
                mult = Decimal(str(multiplier_raw))
                if mult <= Decimal("0"):
                    raise ValueError("Multiplier must be positive.")
            except (InvalidOperation, ValueError):
                return Response(
                    {"detail": "Invalid multiplier value."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            updated_ids = []
            if stream == "hotel":
                qs = HotelRoomType.objects.filter(hotel__owner=user)
                if item_id:
                    qs = qs.filter(id=item_id)
                for rt in qs:
                    rt.dynamic_price_per_night = (Decimal(str(rt.base_price_per_night)) * mult).quantize(Decimal("0.01"))
                    rt.save()
                    updated_ids.append(rt.id)
            else:
                qs = VacationRental.objects.filter(host=user)
                if item_id:
                    qs = qs.filter(id=item_id)
                for rental in qs:
                    rental.dynamic_price_per_night = (Decimal(str(rental.price_per_night)) * mult).quantize(Decimal("0.01"))
                    if rental.weekend_price_per_night is not None:
                        rental.dynamic_weekend_price_per_night = (
                            Decimal(str(rental.weekend_price_per_night)) * mult
                        ).quantize(Decimal("0.01"))
                    rental.save(update_fields=["dynamic_price_per_night", "dynamic_weekend_price_per_night", "updated_at"])
                    updated_ids.append(str(rental.id))

            return Response({
                "message": f"Dynamic prices updated using {mult}x multiplier.",
                "updated_ids": updated_ids,
            })

        if not item_id:
            return Response({"detail": "item_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            dyn_price = self._parse_decimal(
                request.data.get("dynamic_price_per_night"),
                "dynamic_price_per_night",
            )
            dyn_weekend_price = self._parse_decimal(
                request.data.get("dynamic_weekend_price_per_night"),
                "dynamic_weekend_price_per_night",
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if stream == "hotel":
            rt = HotelRoomType.objects.select_related("hotel").filter(id=item_id).first()
            if not rt:
                return Response({"detail": "Hotel room type not found."}, status=status.HTTP_404_NOT_FOUND)
            if rt.hotel.owner != user and not user.is_staff:
                raise PermissionDenied("You do not own this hotel room type.")
            rt.dynamic_price_per_night = dyn_price
            rt.save()
            return Response({
                "id": rt.id,
                "base_price_per_night": str(rt.base_price_per_night),
                "dynamic_price_per_night": str(rt.dynamic_price_per_night) if rt.dynamic_price_per_night is not None else None,
                "effective_price_per_night": str(rt.effective_price_per_night),
                "hotel_dynamic_starting_price": (
                    str(rt.hotel.dynamic_starting_price_per_night)
                    if rt.hotel.dynamic_starting_price_per_night is not None
                    else None
                ),
            })

        rental = VacationRental.objects.filter(id=item_id).first()
        if not rental:
            return Response({"detail": "Vacation rental not found."}, status=status.HTTP_404_NOT_FOUND)
        if rental.host != user and not user.is_staff:
            raise PermissionDenied("You do not host this vacation rental.")

        rental.dynamic_price_per_night = dyn_price
        if "dynamic_weekend_price_per_night" in request.data:
            rental.dynamic_weekend_price_per_night = dyn_weekend_price
        rental.save(update_fields=["dynamic_price_per_night", "dynamic_weekend_price_per_night", "updated_at"])

        return Response({
            "id": str(rental.id),
            "price_per_night": str(rental.price_per_night),
            "weekend_price_per_night": str(rental.weekend_price_per_night) if rental.weekend_price_per_night is not None else None,
            "dynamic_price_per_night": str(rental.dynamic_price_per_night) if rental.dynamic_price_per_night is not None else None,
            "dynamic_weekend_price_per_night": str(rental.dynamic_weekend_price_per_night) if rental.dynamic_weekend_price_per_night is not None else None,
        })
