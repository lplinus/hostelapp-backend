import math
from decimal import Decimal
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.apps import apps
from .models import PropertyPinpoint
from .serializers import (
    PropertyPinpointSerializer,
    AutoFetchPinpointSerializer,
)


class PropertyPinpointViewSet(viewsets.ModelViewSet):
    queryset = PropertyPinpoint.objects.all()
    serializer_class = PropertyPinpointSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        property_type = self.request.query_params.get("property_type")
        property_id = self.request.query_params.get("property_id")
        owner_only = self.request.query_params.get("owner_only")

        if property_type:
            qs = qs.filter(property_type=property_type)
        if property_id:
            qs = qs.filter(property_id=property_id)
        if owner_only and self.request.user.is_authenticated:
            qs = qs.filter(owner=self.request.user)

        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=False, methods=["post"], url_path="auto-fetch", permission_classes=[permissions.IsAuthenticated])
    def auto_fetch_location(self, request):
        """
        Receives device geolocation / GPS coordinates, saves the pinpoint,
        and optionally synchronizes lat/lng directly to the parent property record.
        """
        serializer = AutoFetchPinpointSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        prop_type = d.get("property_type")
        prop_id = d.get("property_id")
        lat = d["latitude"]
        lng = d["longitude"]
        accuracy = d.get("accuracy")

        # Find existing or create new pinpoint
        pinpoint = None
        if prop_id:
            pinpoint = PropertyPinpoint.objects.filter(
                property_type=prop_type,
                property_id=prop_id,
                owner=request.user,
            ).first()

        title = d.get("title") or f"{prop_type.replace('_', ' ').title()} Location"

        if pinpoint:
            pinpoint.latitude = lat
            pinpoint.longitude = lng
            pinpoint.is_auto_fetched = True
            pinpoint.gps_accuracy = accuracy
            if d.get("formatted_address"):
                pinpoint.formatted_address = d["formatted_address"]
            if d.get("landmark"):
                pinpoint.landmark = d["landmark"]
            if d.get("directions_guide"):
                pinpoint.directions_guide = d["directions_guide"]
            pinpoint.offline_tile_bounds = pinpoint.calculate_offline_bounds()
            pinpoint.save()
        else:
            pinpoint = PropertyPinpoint.objects.create(
                owner=request.user,
                property_type=prop_type,
                property_id=prop_id,
                title=title,
                latitude=lat,
                longitude=lng,
                formatted_address=d.get("formatted_address") or "",
                landmark=d.get("landmark") or "",
                directions_guide=d.get("directions_guide") or "",
                is_auto_fetched=True,
                gps_accuracy=accuracy,
            )

        # Synchronize latitude and longitude to the underlying property table
        if d.get("sync_property_record", True) and prop_id:
            self._sync_coordinates_to_property(prop_type, prop_id, lat, lng)

        return Response(
            {
                "message": "Pinpoint automatically saved and synchronized successfully.",
                "pinpoint": PropertyPinpointSerializer(pinpoint).data,
            },
            status=status.HTTP_200_OK,
        )

    def _sync_coordinates_to_property(self, prop_type: str, prop_id: int, lat: Decimal, lng: Decimal):
        try:
            if prop_type == "hostel":
                Hostel = apps.get_model("hostels", "Hostel")
                Hostel.objects.filter(id=prop_id).update(latitude=lat, longitude=lng)
            elif prop_type == "hotel":
                Hotel = apps.get_model("hotels", "Hotel")
                Hotel.objects.filter(id=prop_id).update(latitude=lat, longitude=lng)
            elif prop_type == "vacation_rental":
                VacationRental = apps.get_model("vacanationrentals", "VacationRental")
                VacationRental.objects.filter(id=prop_id).update(latitude=lat, longitude=lng)
        except Exception as e:
            # Non-blocking sync error
            print(f"Error syncing coordinates to {prop_type} #{prop_id}: {e}")

    @action(detail=False, methods=["get"], url_path="offline-package")
    def get_offline_package(self, request):
        """
        Returns full offline bundle: pinpoint, bounding box, route guidance,
        and tile caching specs for low-connectivity offline use.
        """
        prop_type = request.query_params.get("property_type")
        prop_id = request.query_params.get("property_id")

        if not prop_type or not prop_id:
            return Response(
                {"detail": "property_type and property_id query params are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        pinpoint = PropertyPinpoint.objects.filter(
            property_type=prop_type,
            property_id=prop_id,
        ).first()

        if not pinpoint:
            return Response(
                {"detail": "No pinpoint found for this property."},
                status=status.HTTP_404_NOT_FOUND,
            )

        bounds = pinpoint.offline_tile_bounds or pinpoint.calculate_offline_bounds()

        return Response({
            "pinpoint": PropertyPinpointSerializer(pinpoint).data,
            "offline_tile_bounds": bounds,
            "center": {
                "latitude": float(pinpoint.latitude),
                "longitude": float(pinpoint.longitude),
            },
            "offline_tile_template": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "recommended_zoom_range": [14, 15, 16, 17, 18],
            "directions_guide": pinpoint.directions_guide or "Follow primary road to the pinpoint landmark.",
            "landmark": pinpoint.landmark or "",
        })

    @action(detail=False, methods=["get"], url_path="nearby")
    def nearby(self, request):
        """
        Radius search for nearby property pinpoints using Haversine formula.
        """
        lat_str = request.query_params.get("lat")
        lng_str = request.query_params.get("lng")
        radius_km = float(request.query_params.get("radius_km", 10.0))

        if not lat_str or not lng_str:
            return Response(
                {"detail": "lat and lng query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_lat = float(lat_str)
        target_lng = float(lng_str)

        all_pinpoints = PropertyPinpoint.objects.all()
        nearby_results = []

        for p in all_pinpoints:
            try:
                plat = float(p.latitude)
                plng = float(p.longitude)

                # Haversine formula
                dlat = math.radians(plat - target_lat)
                dlng = math.radians(plng - target_lng)
                a = (
                    math.sin(dlat / 2) ** 2
                    + math.cos(math.radians(target_lat))
                    * math.cos(math.radians(plat))
                    * math.sin(dlng / 2) ** 2
                )
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                dist = 6371.0 * c  # Earth radius in KM

                if dist <= radius_km:
                    data = PropertyPinpointSerializer(p).data
                    data["distance_km"] = round(dist, 2)
                    nearby_results.append(data)
            except (ValueError, TypeError):
                continue

        nearby_results.sort(key=lambda x: x["distance_km"])
        return Response(nearby_results)
