import django_filters
from django.db.models import Q
from .models import Hotel
from .search import search_hotels


class HotelFilter(django_filters.FilterSet):
    # Search query
    q = django_filters.CharFilter(method="filter_search")
    search = django_filters.CharFilter(method="filter_search")
    searchQuery = django_filters.CharFilter(method="filter_search")

    # Star rating: supports comma-separated list e.g. "3,4,5" or single or multiple params
    star_rating = django_filters.CharFilter(method="filter_star_ratings")
    star_ratings = django_filters.CharFilter(method="filter_star_ratings")
    min_star_rating = django_filters.NumberFilter(field_name="star_rating", lookup_expr="gte")
    max_star_rating = django_filters.NumberFilter(field_name="star_rating", lookup_expr="lte")

    # Hotel type: supports comma-separated list e.g. "luxury,boutique" or single
    hotel_type = django_filters.CharFilter(method="filter_hotel_types")
    hotel_types = django_filters.CharFilter(method="filter_hotel_types")

    # Pricing
    min_price = django_filters.NumberFilter(field_name="starting_price_per_night", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="starting_price_per_night", lookup_expr="lte")
    starting_price_per_night = django_filters.NumberFilter(field_name="starting_price_per_night", lookup_expr="lte")

    # Cancellation & Rules
    free_cancellation = django_filters.BooleanFilter(method="filter_free_cancellation")
    freeCancellationOnly = django_filters.BooleanFilter(method="filter_free_cancellation")
    allows_pets = django_filters.BooleanFilter(field_name="allows_pets")
    petsAllowedOnly = django_filters.BooleanFilter(field_name="allows_pets")

    # Amenities: supports comma-separated amenity names or slugs
    amenities = django_filters.CharFilter(method="filter_amenities")
    selectedAmenities = django_filters.CharFilter(method="filter_amenities")

    # Location
    city = django_filters.CharFilter(method="filter_city")
    area = django_filters.CharFilter(method="filter_area")

    # Badges
    is_featured = django_filters.BooleanFilter(field_name="is_featured")
    is_toprated = django_filters.BooleanFilter(field_name="is_toprated")

    class Meta:
        model = Hotel
        fields = [
            "hotel_type",
            "star_rating",
            "city",
            "area",
            "allows_pets",
            "is_featured",
            "is_toprated",
            "cancellation_policy",
        ]

    def filter_search(self, queryset, name, value):
        return search_hotels(queryset, value)

    def filter_star_ratings(self, queryset, name, value):
        if not value:
            return queryset
        if isinstance(value, str):
            tokens = [t.strip() for t in value.split(",") if t.strip()]
        elif isinstance(value, (list, tuple)):
            tokens = [str(t).strip() for t in value if str(t).strip()]
        else:
            tokens = [str(value).strip()]

        ratings = []
        for t in tokens:
            try:
                ratings.append(int(t))
            except ValueError:
                pass

        if ratings:
            return queryset.filter(star_rating__in=ratings)
        return queryset

    def filter_hotel_types(self, queryset, name, value):
        if not value:
            return queryset
        if isinstance(value, str):
            types = [t.strip().lower() for t in value.split(",") if t.strip()]
        elif isinstance(value, (list, tuple)):
            types = [str(t).strip().lower() for t in value if str(t).strip()]
        else:
            types = [str(value).strip().lower()]

        if types:
            return queryset.filter(hotel_type__in=types)
        return queryset

    def filter_free_cancellation(self, queryset, name, value):
        if value:
            return queryset.filter(cancellation_policy=Hotel.CancellationPolicy.FREE_CANCELLATION)
        return queryset

    def filter_amenities(self, queryset, name, value):
        if not value:
            return queryset
        if isinstance(value, str):
            amenity_list = [a.strip() for a in value.split(",") if a.strip()]
        elif isinstance(value, (list, tuple)):
            amenity_list = [str(a).strip() for a in value if str(a).strip()]
        else:
            amenity_list = [str(value).strip()]

        for amenity in amenity_list:
            queryset = queryset.filter(
                Q(amenities__name__icontains=amenity) | Q(amenities__slug__iexact=amenity)
            )
        return queryset.distinct()

    def filter_city(self, queryset, name, value):
        if not value:
            return queryset
        val = str(value).strip()
        if val.isdigit():
            return queryset.filter(city_id=int(val))
        return queryset.filter(Q(city__name__icontains=val) | Q(city__slug__iexact=val))

    def filter_area(self, queryset, name, value):
        if not value:
            return queryset
        val = str(value).strip()
        if val.isdigit():
            return queryset.filter(area_id=int(val))
        return queryset.filter(Q(area__name__icontains=val) | Q(area__slug__iexact=val))
