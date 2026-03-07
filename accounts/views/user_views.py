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

        # Determine stats based on user role
        if user.role == "hostel_owner":
            # Stats for the owner's properties
            total_hostels = Hostel.objects.filter(owner=user).count()

            # Count total rooms in owner's hostels.
            # Using RoomType count as rooms count.
            total_rooms = sum(
                [h.room_types.count() for h in Hostel.objects.filter(owner=user)]
            )

            active_bookings = Booking.objects.filter(
                hostel__owner=user, status="confirmed"
            ).count()

            # Revenue calculation from confirmed bookings or payments
            # Summing the total_price of confirmed bookings
            revenue_agg = Booking.objects.filter(
                hostel__owner=user, status="confirmed"
            ).aggregate(Sum("total_price"))
            revenue = revenue_agg["total_price__sum"] or 0
        else:
            # Stats for guest (or all stats if admin, but requirement states just simple counts)
            # Example response from prompt: total_hostels: 12, total_rooms: 120, etc.
            # Stats for guest or other roles should also reflect their own properties (which will be 0 if none)
            total_hostels = Hostel.objects.filter(owner=user).count()
            total_rooms = sum(
                [h.room_types.count() for h in Hostel.objects.filter(owner=user)]
            )
            active_bookings = Booking.objects.filter(
                user=user, status="confirmed"
            ).count()
            revenue = (
                Booking.objects.filter(user=user, status="confirmed").aggregate(
                    Sum("total_price")
                )["total_price__sum"]
                or 0
            )

        # Adjust the returned total_rooms logic if needed based on the models.
        # Using RoomType count as rooms count.

        return Response(
            {
                "total_hostels": total_hostels,
                "total_rooms": total_rooms,
                "active_bookings": active_bookings,
                "revenue": float(revenue),
            }
        )
