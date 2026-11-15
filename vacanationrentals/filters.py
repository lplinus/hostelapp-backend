import django_filters
from django.db.models import Q
from .models import VacationRental
from .search import search_vacation_rentals


class VacationRentalFilter(django_filters.FilterSet):
    # Search
    q = django_filters.CharFilter(method="filter_search")
    search = django_filters.CharFilter(method="filter_search")
    searchQuery = django_filters.CharFilter(method="filter_search")

    # Categories: supports comma-separated categories or single e.g. "villa,cottage"
    category = django_filters.CharFilter(method="filter_categories")
    categories = django_filters.CharFilter(method="filter_categories")

    # Rental type
    rental_type = django_filters.CharFilter(method="filter_rental_types")

    # Pricing
    min_price = django_filters.NumberFilter(field_name="price_per_night", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price_per_night", lookup_expr="lte")
    price_per_night = django_filters.NumberFilter(field_name="price_per_night", lookup_expr="lte")

    # Capacity & Bedrooms
    bedrooms = django_filters.NumberFilter(field_name="bedrooms", lookup_expr="gte")
    min_bedrooms = django_filters.NumberFilter(field_name="bedrooms", lookup_expr="gte")
    minBedrooms = django_filters.NumberFilter(field_name="bedrooms", lookup_expr="gte")
    max_guests = django_filters.NumberFilter(field_name="max_guests", lookup_expr="gte")

    # Rules & Badges
    instant_book = django_filters.BooleanFilter(field_name="instant_book")
    instantBookOnly = django_filters.BooleanFilter(field_name="instant_book")
    allows_pets = django_filters.BooleanFilter(field_name="allows_pets")
    petsAllowedOnly = django_filters.BooleanFilter(field_name="allows_pets")
    is_superhost = django_filters.BooleanFilter(field_name="is_superhost")
    superhostOnly = django_filters.BooleanFilter(field_name="is_superhost")
    is_featured = django_filters.BooleanFilter(field_name="is_featured")

    # Amenities
    amenities = django_filters.CharFilter(method="filter_amenities")
    selectedAmenities = django_filters.CharFilter(method="filter_amenities")

    # Location
    city = django_filters.CharFilter(method="filter_city")
    area = django_filters.CharFilter(method="filter_area")

    class Meta:
        model = VacationRental
        fields = [
            "category",
            "rental_type",
            "city",
            "area",
            "instant_book",
            "allows_pets",
            "is_superhost",
            "is_featured",
        ]

    def filter_search(self, queryset, name, value):
        return search_vacation_rentals(queryset, value)

    def filter_categories(self, queryset, name, value):
        if not value or value == "all":
            return queryset
        if isinstance(value, str):
            cats = [c.strip().lower() for c in value.split(",") if c.strip() and c.strip().lower() != "all"]
        elif isinstance(value, (list, tuple)):
            cats = [str(c).strip().lower() for c in value if str(c).strip() and str(c).strip().lower() != "all"]
        else:
            cats = [str(value).strip().lower()]

        if cats:
            return queryset.filter(category__in=cats)
        return queryset

    def filter_rental_types(self, queryset, name, value):
        if not value:
            return queryset
        if isinstance(value, str):
            types = [t.strip().lower() for t in value.split(",") if t.strip()]
        elif isinstance(value, (list, tuple)):
            types = [str(t).strip().lower() for t in value if str(t).strip()]
        else:
            types = [str(value).strip().lower()]
        if types:
            return queryset.filter(rental_type__in=types)
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
