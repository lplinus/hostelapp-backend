import requests as http_requests
from rest_framework import viewsets, permissions, status
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
from .services.search_hostel_service import search_hostels, inner_search_hostels
from hostels.models import Hostel
from hostels.serializers import CityHostelListSerializer


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    lookup_field = "slug"
    pagination_class = None

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class StateViewSet(viewsets.ModelViewSet):
    queryset = State.objects.select_related("country").all()
    serializer_class = StateSerializer
    lookup_field = "slug"
    pagination_class = None

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.select_related("state").all()
    serializer_class = CitySerializer
    lookup_field = "slug"
    pagination_class = None

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAdminUser()]
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]


class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.select_related("city").all()
    serializer_class = AreaSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            return [permissions.IsAdminUser()]
        if self.action == "create":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]


class CityHostelsAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug, *args, **kwargs):
        if slug == "all":
            # Return all active and approved hostels across all cities
            hostels = (
                Hostel.objects.filter(is_active=True, is_approved=True)
                .select_related("area", "city")
                .prefetch_related("images", "room_types")
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


class InnerSearchHostelsAPIView(APIView):
    """
    GET /api/locations/inner-search/?q=...
    Dedicated search for the hostel listing page.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get("q", "").strip()
        city = request.query_params.get("city", "").strip()
        hostel_type = request.query_params.get("type", "").strip()
        room_type = request.query_params.get("room_type", "").strip()
        sharing = request.query_params.get("sharing", "").strip()

        hostels = inner_search_hostels(
            query=query,
            city=city,
            hostel_type=hostel_type,
            room_type=room_type,
            sharing=sharing,
        )
        serializer = CityHostelListSerializer(
            hostels, many=True, context={"request": request}
        )

        return Response(
            {
                "query": query,
                "city": city,
                "type": hostel_type,
                "room_type": room_type,
                "sharing": sharing,
                "total": hostels.count(),
                "results": serializer.data,
            }
        )


class ForwardGeocodeAPIView(APIView):
    """
    GET /api/locations/geocode/?address=...&limit=5
    Server-side forward geocoding using Nominatim.
    Handles Google Maps URLs, cleans noisy addresses, and tries
    progressively simpler queries for best accuracy.
    """

    permission_classes = [permissions.AllowAny]

    # ── helpers ──────────────────────────────────────────────

    @staticmethod
    def _extract_from_google_maps_url(text):
        """
        If the text is a Google Maps URL, extract the address from the URL path.
        e.g. google.com/maps/place/Story+Houz+-+Rare,+Plot+%23+255,...
        Returns the extracted address string, or None if not a Maps URL.
        """
        import re
        from urllib.parse import unquote_plus

        # Match google.com/maps/place/<address>/... or maps.google.com/...
        pattern = r"(?:google\.com|maps\.google\.com)/maps/place/([^/]+)"
        match = re.search(pattern, text)
        if match:
            raw = unquote_plus(match.group(1))
            # Remove business name prefix (anything before the actual address)
            # Business names are usually separated by ", " from the address
            # e.g. "Story Houz - Rare, Plot # 255, VIP Hills, ..."
            # We keep everything after the first comma if the first part
            # doesn't look like a street/area.
            return raw
        return None

    @staticmethod
    def _clean_address(address):
        """
        Remove noise from Indian addresses that confuses Nominatim:
        - Plot/House/Door numbers (Plot # 255, H.No 3-4-5, etc.)
        - "Near XYZ" phrases
        - Parenthetical content like (M), (V), (Mandal)
        - Business/brand names at the start
        - Special characters
        """
        import re

        cleaned = address

        # Remove parenthetical content like (M), (V), (Mandal)
        cleaned = re.sub(r"\([^)]*\)", "", cleaned)

        # Remove "Near ..." up to the next comma
        cleaned = re.sub(r"(?i)\b(?:near|opp|opposite|beside|behind|next to)\s+[^,]+", "", cleaned)

        # Remove Plot/House/Door/H.No numbers
        cleaned = re.sub(r"(?i)\b(?:plot|h\.?no|house|door|flat|room)\s*#?\s*[\d\-/]+", "", cleaned)

        # Remove standalone numbers with special chars (like "3-4-5/A")
        cleaned = re.sub(r"\b\d+[\-/]\d+[\-/\w]*\b", "", cleaned)

        # Remove # followed by numbers
        cleaned = re.sub(r"#\s*\d+", "", cleaned)

        # Remove extra commas, spaces, leading/trailing cleanup
        cleaned = re.sub(r",\s*,", ",", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = cleaned.strip(", ")

        return cleaned

    def _nominatim_search(self, query, limit=5):
        """Call Nominatim search with India bias and return results."""
        resp = http_requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "json",
                "addressdetails": 1,
                "limit": limit,
                "accept-language": "en",
                "countrycodes": "in",
            },
            headers={
                "Accept-Language": "en",
                "User-Agent": "HostelIn-Hostel-Management-App/1.0",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def _search_with_strategies(self, address, limit):
        """
        Try multiple search strategies in order of specificity:
        1. Full cleaned address
        2. Progressive strip from the left (remove first comma-part)
        3. Extract city + state + pincode only
        """
        import re

        strategies = []

        # Strategy 1: cleaned address
        cleaned = self._clean_address(address)
        if cleaned:
            strategies.append(cleaned)

        # Strategy 2: progressively shorter (strip from left)
        parts = [p.strip() for p in cleaned.split(",") if p.strip()]
        for i in range(1, len(parts)):
            shorter = ", ".join(parts[i:])
            if len(shorter) >= 3:
                strategies.append(shorter)

        # Strategy 3: extract pincode + city/state
        pincode_match = re.search(r"\b\d{6}\b", address)
        if pincode_match:
            strategies.append(pincode_match.group())

        # Try each strategy until we get results
        for query in strategies:
            data = self._nominatim_search(query, limit)
            if data:
                return data

        return []

    # ── main view ────────────────────────────────────────────

    def get(self, request, *args, **kwargs):
        raw_input = request.query_params.get("address", "").strip()
        if not raw_input or len(raw_input) < 3:
            return Response(
                {"error": "Address query is too short (min 3 characters)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = min(int(request.query_params.get("limit", 5)), 10)

        try:
            # Check if the input is a Google Maps URL
            extracted = self._extract_from_google_maps_url(raw_input)
            address = extracted if extracted else raw_input

            # Try direct search first (might work for simple addresses)
            data = self._nominatim_search(address, limit)

            # If no results, use multi-strategy search
            if not data:
                data = self._search_with_strategies(address, limit)

            if not data:
                return Response(
                    {"error": "No results found for the given address."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            results = [
                {
                    "lat": float(r["lat"]),
                    "lng": float(r["lon"]),
                    "display_name": r.get("display_name", address),
                }
                for r in data
            ]

            return Response({"results": results})

        except http_requests.exceptions.Timeout:
            return Response(
                {"error": "Geocoding service timed out. Please try again."},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except http_requests.exceptions.RequestException as e:
            return Response(
                {"error": f"Geocoding service error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
