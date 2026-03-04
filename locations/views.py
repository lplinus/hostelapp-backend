from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Country, State, City, Area
from .serializers import (
    CountrySerializer,
    StateSerializer,
    CitySerializer,
    AreaSerializer,
)
from .services.city_hostel_service import get_hostels_by_city
from .services.search_hostel_service import search_hostels
from hostels.models import Hostel
from hostels.serializers import CityHostelListSerializer


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"


class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.select_related("country").all()
    serializer_class = StateSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.select_related("state").all()
    serializer_class = CitySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"


class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.select_related("city").all()
    serializer_class = AreaSerializer
    permission_classes = [permissions.AllowAny]


class CityHostelsAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug, *args, **kwargs):
        if slug == "all":
            # Return all active hostels across all cities
            hostels = (
                Hostel.objects.filter(is_active=True)
                .select_related("area", "city")
                .prefetch_related("images")
                .order_by("-rating_avg")
            )
            serializer = CityHostelListSerializer(
                hostels, many=True, context={"request": request}
            )
            return Response(
                {
                    "city": "All Cities",
                    "total": hostels.count(),
                    "results": serializer.data,
                }
            )

        city, hostels = get_hostels_by_city(slug)
        serializer = CityHostelListSerializer(
            hostels, many=True, context={"request": request}
        )

        return Response(
            {"city": city.name, "total": hostels.count(), "results": serializer.data}
        )


class SearchHostelsAPIView(APIView):
    """
    GET /api/locations/search/?location=...&budget=...&gender=...
    Searches hostels by name, city, or area.
    Returns same format as city/type endpoints for frontend reuse.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get("location", "").strip()
        budget_str = request.query_params.get("budget", "")
        gender = request.query_params.get("gender", "").strip()

        budget = None
        if budget_str:
            try:
                budget = int(budget_str)
            except ValueError:
                pass

        hostels = search_hostels(query=query, budget=budget, gender=gender)
        serializer = CityHostelListSerializer(
            hostels, many=True, context={"request": request}
        )

        return Response(
            {
                "query": query,
                "budget": budget,
                "gender": gender,
                "total": hostels.count(),
                "results": serializer.data,
            }
        )
