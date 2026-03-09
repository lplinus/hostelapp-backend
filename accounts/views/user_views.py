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
    """GET /api/dashboard/stats/ — Returns statistics for the user dashboard."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        from django.db.models import Q, Count
        from django.db.models.functions import TruncMonth

        # All bookings where user is either guest or owner
        related_bookings = Booking.objects.filter(Q(user=user) | Q(hostel__owner=user))

        total_hostels = Hostel.objects.filter(owner=user).count()
        total_rooms = sum(
            [h.room_types.count() for h in Hostel.objects.filter(owner=user)]
        )

        active_bookings = related_bookings.filter(status="confirmed").count()
        total_bookings = related_bookings.filter(
            status__in=["confirmed", "completed", "pending"]
        ).count()
        cancelled_bookings = related_bookings.filter(status="cancelled").count()

        revenue_sum = related_bookings.filter(
            status__in=["confirmed", "completed"]
        ).aggregate(Sum("total_price"))
        revenue = revenue_sum["total_price__sum"] or 0

        # Monthly chart data (last 6 months)
        chart_data_query = (
            related_bookings.annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )

        chart_data = [
            {
                "month": item["month"].strftime("%b %Y"),
                "count": item["count"],
            }
            for item in chart_data_query
        ]

        return Response(
            {
                "total_hostels": total_hostels,
                "total_rooms": total_rooms,
                "active_bookings": active_bookings,
                "total_bookings": total_bookings,
                "cancelled_bookings": cancelled_bookings,
                "revenue": float(revenue),
                "chart_data": chart_data,
            }
        )
