from locations.models import City
from hostels.models import Hostel
from django.shortcuts import get_object_or_404


def get_hostels_by_city(city_slug: str):
    city = get_object_or_404(City, slug=city_slug)

    hostels = (
        Hostel.objects.filter(city=city, is_active=True)
        .select_related("area", "city")
        .prefetch_related("images")
        .order_by("-rating_avg")
    )

    return city, hostels
