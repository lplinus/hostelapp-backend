from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.models import User
from accounts.serializers.user_serializer import UserSerializer, UserProfileSerializer
from hostels.models import Hostel
from rooms.models import RoomType
from bookings.models import Booking
from payments.models import Payment
from django.db.models import Sum


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]


class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        # Don't allow changing role or other protected fields via patch, handled by UserProfileSerializer read_only_fields
        serializer = UserProfileSerializer(
            request.user, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class DashboardStatsView(APIView):
    """
    GET /api/dashboard/stats/ — Returns statistics for the user dashboard.
    Unified across Hostels, Hotels, and Vacation Rentals without filtering any property stream out.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        from django.db.models import Q, Sum
        from collections import defaultdict
        from hostels.models import Hostel
        from bookings.models import Booking
        from hotels.models import Hotel, HotelBooking, HotelRoomType
        from vacanationrentals.models import VacationRental, VacationRentalBooking

        # 1. Properties & Rooms Breakdown
        hostels_count = Hostel.objects.filter(owner=user).count()
        hotels_count = Hotel.objects.filter(owner=user).count()
        rentals_count = VacationRental.objects.filter(host=user).count()
        total_properties = hostels_count + hotels_count + rentals_count

        hostel_rooms = sum(
            [h.room_types.count() for h in Hostel.objects.filter(owner=user)]
        )
        hotel_rooms = HotelRoomType.objects.filter(hotel__owner=user).count()
        rental_units = rentals_count
        total_rooms = hostel_rooms + hotel_rooms + rental_units

        # 2. Query Bookings across all 3 property domains
        hostel_bookings = Booking.objects.filter(Q(owner=user) | Q(hostel__owner=user) | Q(user=user))
        hotel_bookings = HotelBooking.objects.filter(Q(owner=user) | Q(hotel__owner=user) | Q(user=user))
        rental_bookings = VacationRentalBooking.objects.filter(
            Q(host=user) | Q(owner=user) | Q(rental__host=user) | Q(user=user)
        )

        # 3. Active Bookings (Confirmed)
        active_hostel = hostel_bookings.filter(status="confirmed").count()
        active_hotel = hotel_bookings.filter(status=HotelBooking.BookingStatus.CONFIRMED).count()
        active_rental = rental_bookings.filter(status=VacationRentalBooking.BookingStatus.CONFIRMED).count()
        active_bookings = active_hostel + active_hotel + active_rental

        # 4. Total Bookings (Confirmed, Completed/Checked-in, Pending)
        total_hostel = hostel_bookings.filter(status__in=["confirmed", "completed", "pending"]).count()
        total_hotel = hotel_bookings.filter(
            status__in=["confirmed", "checked_in", "checked_out", "pending"]
        ).count()
        total_rental = rental_bookings.filter(
            status__in=["confirmed", "checked_in", "completed", "pending_approval"]
        ).count()
        total_bookings = total_hostel + total_hotel + total_rental

        # 5. Cancelled Bookings
        cancelled_hostel = hostel_bookings.filter(status="cancelled").count()
        cancelled_hotel = hotel_bookings.filter(status=HotelBooking.BookingStatus.CANCELLED).count()
        cancelled_rental = rental_bookings.filter(status=VacationRentalBooking.BookingStatus.CANCELLED).count()
        cancelled_bookings = cancelled_hostel + cancelled_hotel + cancelled_rental

        # 6. Revenue Aggregation
        hostel_rev = (
            hostel_bookings.filter(status__in=["confirmed", "completed"]).aggregate(Sum("total_price"))[
                "total_price__sum"
            ]
            or 0
        )
        hotel_rev = (
            hotel_bookings.filter(
                status__in=["confirmed", "checked_in", "checked_out"]
            ).aggregate(Sum("total_amount"))["total_amount__sum"]
            or 0
        )
        rental_rev = (
            rental_bookings.filter(
                status__in=["confirmed", "checked_in", "completed"]
            ).aggregate(Sum("total_price"))["total_price__sum"]
            or 0
        )
        total_revenue = float(hostel_rev) + float(hotel_rev) + float(rental_rev)

        # 7. Unified Monthly Chart Data & Daily Timeline Data per Stream (Hostels, Hotels, Vacation Rentals, All)
        monthly_map = defaultdict(int)
        from datetime import datetime

        def init_timeline_map():
            return defaultdict(lambda: {"confirmed": 0, "cancelled": 0, "total": 0})

        stream_timelines = {
            "all": init_timeline_map(),
            "hostel": init_timeline_map(),
            "hotel": init_timeline_map(),
            "vacation_rental": init_timeline_map(),
        }

        # Track hostel bookings
        for b in hostel_bookings.only("created_at", "status"):
            if b.created_at:
                m_key = b.created_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                monthly_map[m_key] += 1

                d_key = b.created_at.strftime("%Y-%m-%d")
                for s in ["all", "hostel"]:
                    stream_timelines[s][d_key]["total"] += 1
                    if b.status == "cancelled":
                        stream_timelines[s][d_key]["cancelled"] += 1
                    else:
                        stream_timelines[s][d_key]["confirmed"] += 1

        # Track hotel bookings
        for b in hotel_bookings.only("created_at", "status"):
            if b.created_at:
                m_key = b.created_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                monthly_map[m_key] += 1

                d_key = b.created_at.strftime("%Y-%m-%d")
                for s in ["all", "hotel"]:
                    stream_timelines[s][d_key]["total"] += 1
                    if b.status == HotelBooking.BookingStatus.CANCELLED:
                        stream_timelines[s][d_key]["cancelled"] += 1
                    else:
                        stream_timelines[s][d_key]["confirmed"] += 1

        # Track vacation rental bookings
        for b in rental_bookings.only("created_at", "status"):
            if b.created_at:
                m_key = b.created_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                monthly_map[m_key] += 1

                d_key = b.created_at.strftime("%Y-%m-%d")
                for s in ["all", "vacation_rental"]:
                    stream_timelines[s][d_key]["total"] += 1
                    if b.status == VacationRentalBooking.BookingStatus.CANCELLED:
                        stream_timelines[s][d_key]["cancelled"] += 1
                    else:
                        stream_timelines[s][d_key]["confirmed"] += 1

        sorted_months = sorted(monthly_map.keys())[-6:] if monthly_map else []
        chart_data = [
            {
                "month": dt.strftime("%b %Y"),
                "count": monthly_map[dt],
            }
            for dt in sorted_months
        ]

        def format_timeline(t_map):
            sorted_dates = sorted(t_map.keys())
            return [
                {
                    "date": date_str,
                    "label": datetime.strptime(date_str, "%Y-%m-%d").strftime("%b %d"),
                    "day": datetime.strptime(date_str, "%Y-%m-%d").strftime("%a"),
                    "confirmed": t_map[date_str]["confirmed"],
                    "cancelled": t_map[date_str]["cancelled"],
                    "total": t_map[date_str]["total"],
                }
                for date_str in sorted_dates
            ]

        streams = {
            "all": {
                "total": total_bookings,
                "cancelled": cancelled_bookings,
                "confirmed": total_bookings - cancelled_bookings if total_bookings >= cancelled_bookings else active_bookings,
                "properties": total_properties,
                "rooms": total_rooms,
                "revenue": round(total_revenue, 2),
                "timeline": format_timeline(stream_timelines["all"]),
            },
            "hostel": {
                "total": total_hostel,
                "cancelled": cancelled_hostel,
                "confirmed": total_hostel - cancelled_hostel if total_hostel >= cancelled_hostel else active_hostel,
                "properties": hostels_count,
                "rooms": hostel_rooms,
                "revenue": round(float(hostel_rev), 2),
                "timeline": format_timeline(stream_timelines["hostel"]),
            },
            "hotel": {
                "total": total_hotel,
                "cancelled": cancelled_hotel,
                "confirmed": total_hotel - cancelled_hotel if total_hotel >= cancelled_hotel else active_hotel,
                "properties": hotels_count,
                "rooms": hotel_rooms,
                "revenue": round(float(hotel_rev), 2),
                "timeline": format_timeline(stream_timelines["hotel"]),
            },
            "vacation_rental": {
                "total": total_rental,
                "cancelled": cancelled_rental,
                "confirmed": total_rental - cancelled_rental if total_rental >= cancelled_rental else active_rental,
                "properties": rentals_count,
                "rooms": rental_units,
                "revenue": round(float(rental_rev), 2),
                "timeline": format_timeline(stream_timelines["vacation_rental"]),
            },
        }

        timeline = streams["all"]["timeline"]

        return Response(
            {
                # Backward-compatible keys expected by frontend components
                "total_hostels": total_properties,
                "total_rooms": total_rooms,
                "active_bookings": active_bookings,
                "total_bookings": total_bookings,
                "cancelled_bookings": cancelled_bookings,
                "revenue": round(total_revenue, 2),
                "chart_data": chart_data,
                "timeline": timeline,
                "streams": streams,
                # Explicit domain breakdown for advanced dashboard widgets
                "properties_breakdown": {
                    "hostels": hostels_count,
                    "hotels": hotels_count,
                    "vacation_rentals": rentals_count,
                    "total": total_properties,
                },
                "revenue_breakdown": {
                    "hostels": float(hostel_rev),
                    "hotels": float(hotel_rev),
                    "vacation_rentals": float(rental_rev),
                },
            }
        )


class OwnerAllBookingsView(APIView):
    """
    GET /api/dashboard/all-bookings/ — Unified bookings endpoint for the owner dashboard.
    Returns normalized bookings across hostels, hotels, and vacation rentals.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        from django.db.models import Q
        from bookings.models import Booking
        from hotels.models import HotelBooking
        from vacanationrentals.models import VacationRentalBooking

        unified_list = []

        # 1. Hostel Bookings
        hostel_b_qs = Booking.objects.filter(
            Q(owner=user) | Q(hostel__owner=user)
        ).select_related("hostel", "room_type", "user", "review")
        for b in hostel_b_qs:
            has_rev = hasattr(b, "review") and b.review is not None
            unified_list.append({
                "id": str(b.id),
                "booking_reference": f"STN-{str(b.id)[:8].upper()}",
                "property_type": "hostel",
                "property_name": getattr(b.hostel, "name", "Hostel"),
                "room_type": getattr(b.room_type, "name", "Standard Room") if b.room_type else "Room",
                "guest_name": b.guest_name or "Guest",
                "guest_email": b.guest_email or "",
                "mobile_number": b.mobile_number or "",
                "check_in": b.check_in,
                "check_out": b.check_out,
                "total_price": float(b.total_price),
                "status": b.status,
                "payment_method": b.payment_method,
                "payment_status": b.payment_status,
                "has_reviewed": has_rev,
                "review_rating": b.review.rating if has_rev else None,
                "created_at": b.created_at,
            })

        # 2. Hotel Bookings
        hotel_b_qs = HotelBooking.objects.filter(
            Q(owner=user) | Q(hotel__owner=user)
        ).select_related("hotel", "room_type", "guest_details", "payment_details", "review")
        for hb in hotel_b_qs:
            g = getattr(hb, "guest_details", None)
            p = getattr(hb, "payment_details", None)
            has_rev = hasattr(hb, "review") and hb.review is not None
            unified_list.append({
                "id": str(hb.id),
                "booking_reference": hb.booking_reference,
                "property_type": "hotel",
                "property_name": getattr(hb.hotel, "name", "Hotel"),
                "room_type": getattr(hb.room_type, "name", "Room"),
                "guest_name": g.guest_name if g else "Guest",
                "guest_email": g.guest_email if g else "",
                "mobile_number": g.mobile_number if g else "",
                "check_in": hb.check_in_date,
                "check_out": hb.check_out_date,
                "total_price": float(hb.total_amount),
                "status": hb.status,
                "payment_method": p.payment_method if p else "online",
                "payment_status": p.payment_status if p else "pending",
                "has_reviewed": has_rev,
                "review_rating": hb.review.rating if has_rev else None,
                "created_at": hb.created_at,
            })

        # 3. Vacation Rental Bookings
        rental_b_qs = VacationRentalBooking.objects.filter(
            Q(host=user) | Q(owner=user) | Q(rental__host=user)
        ).select_related("rental", "guest_details", "pricing_details", "review")
        for rb in rental_b_qs:
            g = getattr(rb, "guest_details", None)
            p = getattr(rb, "pricing_details", None)
            has_rev = hasattr(rb, "review") and rb.review is not None
            unified_list.append({
                "id": str(rb.id),
                "booking_reference": rb.booking_reference,
                "property_type": "vacation_rental",
                "property_name": getattr(rb.rental, "title", "Vacation Rental"),
                "room_type": "Entire Place",
                "guest_name": g.guest_name if g else "Guest",
                "guest_email": g.guest_email if g else "",
                "mobile_number": g.mobile_number if g else "",
                "check_in": rb.check_in_date,
                "check_out": rb.check_out_date,
                "total_price": float(rb.total_price),
                "status": rb.status,
                "payment_method": p.payment_method if p else "online",
                "payment_status": p.payment_status if p else "pending",
                "has_reviewed": has_rev,
                "review_rating": rb.review.rating if has_rev else None,
                "created_at": rb.created_at,
            })

        # Sort combined bookings newest first
        unified_list.sort(key=lambda x: x["created_at"], reverse=True)
        return Response(unified_list)
