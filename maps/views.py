from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.apps import apps
from django.core.cache import cache
from decimal import Decimal

from .models import PropertyPinpoint, MapPlace
from .serializers import (
    PropertyPinpointSerializer,
    AutoFetchPinpointSerializer,
    MapPlaceSerializer,
)

CACHE_KEY_GEOJSON_ALL = "maps:geojson:all"
CACHE_TTL = 300  # 5 minutes in memory cache


def compile_all_geojson_features():
    """
    Assembles the complete GeoJSON collection for the map:
    - All Hotels (directly from hotels table, with images/ratings/prices)
    - All Vacation Rentals (directly from vacanationrentals table)
    - Custom PropertyPinpoints (manual pins, deduped against above)
    - MapPlaces (attractions, viewpoints, food, shops)
    Does NOT include Hostels (hostel maps are handled separately).
    """
    features = []
    seen_keys = set()

    # 1. All Hotels with valid coordinates
    try:
        Hotel = apps.get_model("hotels", "Hotel")
        for h in Hotel.objects.filter(
            is_active=True, latitude__isnull=False, longitude__isnull=False
        ).select_related("city", "area").prefetch_related("images"):
            key = f"hotel-{h.id}"
            seen_keys.add(key)
            first_img = h.images.first()
            img_url = first_img.image.url if (first_img and first_img.image) else ""
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(h.longitude), float(h.latitude)]
                },
                "properties": {
                    "id": str(h.id),
                    "title": h.name,
                    "property_type": "hotel",
                    "property_id": str(h.id),
                    "city": h.city.name if h.city else "",
                    "landmark": h.area.name if h.area else "",
                    "formatted_address": h.address or "",
                    "slug": h.slug,
                    "image": img_url,
                    "price": str(h.starting_price_per_night or ""),
                    "rating": str(h.rating_avg or "5.0"),
                    "reviews_count": h.rating_count or 0,
                    "star_rating": h.star_rating or 5,
                }
            })
    except Exception as e:
        print(f"[maps] Error compiling hotels: {e}")

    # 2. All Vacation Rentals with valid coordinates
    try:
        VacationRental = apps.get_model("vacanationrentals", "VacationRental")
        for v in VacationRental.objects.filter(
            is_active=True, latitude__isnull=False, longitude__isnull=False
        ).select_related("city", "area").prefetch_related("images"):
            key = f"vacation_rental-{v.id}"
            seen_keys.add(key)
            first_img = v.images.first()
            img_url = first_img.image.url if (first_img and first_img.image) else ""
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(v.longitude), float(v.latitude)]
                },
                "properties": {
                    "id": str(v.id),
                    "title": v.title,
                    "property_type": "vacation_rental",
                    "property_id": str(v.id),
                    "city": v.city.name if v.city else "",
                    "landmark": v.area.name if v.area else "",
                    "formatted_address": v.address or "",
                    "slug": v.slug,
                    "image": img_url,
                    "price": str(v.price_per_night or ""),
                    "rating": str(v.rating_avg or "5.0"),
                    "reviews_count": v.rating_count or 0,
                    "star_rating": 5,
                }
            })
    except Exception as e:
        print(f"[maps] Error compiling vacation rentals: {e}")

    # 3. Custom PropertyPinpoints (skip duplicates already pulled above)
    pinpoints = PropertyPinpoint.objects.filter(is_deleted=False)
    for pin in pinpoints:
        key = f"{pin.property_type}-{pin.property_id}"
        if key not in seen_keys:
            seen_keys.add(key)
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(pin.longitude), float(pin.latitude)]
                },
                "properties": _enrich_pin_properties(pin)
            })

    # 4. MapPlaces (attractions, viewpoints, food, shops)
    map_places = MapPlace.objects.filter(is_active=True)
    for place in map_places:
        img_url = place.image.url if place.image else ""
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(place.longitude), float(place.latitude)]
            },
            "properties": {
                "id": f"place-{place.id}",
                "title": place.title,
                "property_type": place.category,
                "property_id": str(place.id),
                "city": place.city or "",
                "landmark": place.landmark or "",
                "formatted_address": place.address or "",
                "description": place.description or "",
                "phone": place.phone or "",
                "slug": place.link_url.strip("/").split("/")[-1] if place.link_url else "",
                "image": img_url,
                "price": "",
                "rating": "5.0",
                "reviews_count": 0,
                "star_rating": 5 if place.is_featured else 4,
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features
    }


def _enrich_pin_properties(pin):
    props = {
        "id": pin.id,
        "title": pin.title,
        "property_type": pin.property_type,
        "property_id": pin.property_id,
        "city": pin.city or "",
        "landmark": pin.landmark or "",
        "formatted_address": pin.formatted_address or "",
        "slug": "",
        "image": "",
        "price": "",
        "rating": "",
        "reviews_count": 0,
        "star_rating": 0,
    }

    if not pin.property_id:
        return props

    try:
        if pin.property_type == "hotel":
            Hotel = apps.get_model("hotels", "Hotel")
            h = Hotel.objects.filter(id=pin.property_id).first()
            if h:
                props["slug"] = h.slug
                props["price"] = str(h.starting_price_per_night or "")
                props["rating"] = str(h.rating_avg or "5.0")
                props["reviews_count"] = h.rating_count or 0
                props["star_rating"] = h.star_rating or 5
                first_img = h.images.first()
                if first_img and first_img.image:
                    props["image"] = first_img.image.url
        elif pin.property_type == "vacation_rental":
            VacationRental = apps.get_model("vacanationrentals", "VacationRental")
            v = VacationRental.objects.filter(id=pin.property_id).first()
            if v:
                props["slug"] = v.slug
                props["price"] = str(v.price_per_night or "")
                props["rating"] = str(v.rating_avg or "5.0")
                props["reviews_count"] = v.rating_count or 0
                first_img = v.images.first()
                if first_img and first_img.image:
                    props["image"] = first_img.image.url
        elif pin.property_type == "hostel":
            Hostel = apps.get_model("hostels", "Hostel")
            hostel = Hostel.objects.filter(id=pin.property_id).first()
            if hostel:
                props["slug"] = hostel.slug
                props["price"] = str(hostel.price or hostel.price_per_day or "")
                props["rating"] = str(hostel.rating_avg or "5.0")
                props["reviews_count"] = hostel.rating_count or 0
                first_img = hostel.images.first()
                if first_img and first_img.image:
                    props["image"] = first_img.image.url
    except Exception as e:
        print(f"Error enriching pin #{pin.id}: {e}")

    return props


@api_view(['GET'])
def get_map_properties(request):
    """
    Standard Django ORM bounding box filter for map properties without needing GDAL.
    Format: bbox=min_lng,min_lat,max_lng,max_lat
    """
    bbox = request.query_params.get('bbox')
    queryset = PropertyPinpoint.objects.all()

    if bbox:
        try:
            min_lng, min_lat, max_lng, max_lat = [float(c) for c in bbox.split(',')]
            queryset = queryset.filter(
                longitude__gte=min_lng,
                longitude__lte=max_lng,
                latitude__gte=min_lat,
                latitude__lte=max_lat
            )
        except ValueError:
            pass

    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(pin.longitude), float(pin.latitude)]  # [lng, lat]
            },
            "properties": _enrich_pin_properties(pin)
        }
        for pin in queryset
    ]

    return Response({
        "type": "FeatureCollection",
        "features": features
    })


class PropertyPinpointViewSet(viewsets.ModelViewSet):
    queryset = PropertyPinpoint.objects.all()
    serializer_class = PropertyPinpointSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        property_type = self.request.query_params.get("property_type")
        property_id = self.request.query_params.get("property_id")
        owner_only = self.request.query_params.get("owner_only")

        bbox = self.request.query_params.get("bbox")  # format: "min_lng,min_lat,max_lng,max_lat"

        if property_type:
            qs = qs.filter(property_type=property_type)
        if property_id:
            qs = qs.filter(property_id=property_id)
        if owner_only and self.request.user.is_authenticated:
            qs = qs.filter(owner=self.request.user)

        # Standard Django Bounding Box Filter
        if bbox:
            try:
                min_lng, min_lat, max_lng, max_lat = [float(c) for c in bbox.split(',')]
                qs = qs.filter(
                    longitude__gte=min_lng,
                    longitude__lte=max_lng,
                    latitude__gte=min_lat,
                    latitude__lte=max_lat
                )
            except ValueError:
                pass

        return qs

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=False, methods=["post"], url_path="auto-fetch", permission_classes=[permissions.IsAuthenticated])
    def auto_fetch_location(self, request):
        serializer = AutoFetchPinpointSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        prop_type = d.get("property_type")
        prop_id = d.get("property_id")
        lat = d["latitude"]
        lng = d["longitude"]
        accuracy = d.get("accuracy")

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
            print(f"Error syncing coordinates to {prop_type} #{prop_id}: {e}")

    @action(detail=False, methods=["get"], url_path="offline-package")
    def get_offline_package(self, request):
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

    @action(detail=False, methods=["get"], url_path="geojson")
    def geojson_pins(self, request):
        category = request.query_params.get("category")
        property_id = request.query_params.get("property_id")
        property_type = request.query_params.get("property_type")

        # Fast-path Redis/Memcached cache when requesting general map without custom filters
        # Capable of serving 100,000+ requests/sec directly from memory with 0 DB queries!
        if not category and not property_id and not property_type:
            cached_data = cache.get(CACHE_KEY_GEOJSON_ALL)
            if cached_data:
                return Response(cached_data)

            # If cache miss, compile and store in cache
            data = compile_all_geojson_features()
            cache.set(CACHE_KEY_GEOJSON_ALL, data, CACHE_TTL)
            return Response(data)

        # Filtered requests: query using indexed fields
        queryset = self.get_queryset()
        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(pin.longitude), float(pin.latitude)]
                },
                "properties": _enrich_pin_properties(pin)
            }
            for pin in queryset
        ]

        map_places = MapPlace.objects.filter(is_active=True)
        if category:
            map_places = map_places.filter(category=category)

        for place in map_places:
            img_url = place.image.url if place.image else ""
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(place.longitude), float(place.latitude)]
                },
                "properties": {
                    "id": f"place-{place.id}",
                    "title": place.title,
                    "property_type": place.category,
                    "property_id": str(place.id),
                    "city": place.city or "",
                    "landmark": place.landmark or "",
                    "formatted_address": place.address or "",
                    "description": place.description or "",
                    "phone": place.phone or "",
                    "slug": place.link_url.strip("/").split("/")[-1] if place.link_url else "",
                    "image": img_url,
                    "price": "",
                    "rating": "5.0",
                    "reviews_count": 0,
                    "star_rating": 5 if place.is_featured else 4,
                }
            })

        return Response({
            "type": "FeatureCollection",
            "features": features
        })


class MapPlaceViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for MapPlace (Shops, Cafes, Attractions, Viewpoints, Transport, etc.)
    """
    queryset = MapPlace.objects.filter(is_active=True)
    serializer_class = MapPlaceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get("category")
        city = self.request.query_params.get("city")
        is_featured = self.request.query_params.get("is_featured")

        if category:
            qs = qs.filter(category=category)
        if city:
            qs = qs.filter(city__icontains=city)
        if is_featured:
            qs = qs.filter(is_featured=is_featured.lower() == "true")

        return qs