from django.db.models import Q
from hostels.models import Hostel


def search_hostels(query: str = "", budget: int = None, gender: str = ""):
    """
    Search active hostels by name, city name, or area name.
    Optionally filter by budget (max price) and gender (hostel_type).
    """
    qs = (
        Hostel.objects.filter(is_active=True)
        .select_related("area", "city")
        .prefetch_related("images")
    )

    # Text search across hostel name, city name, area name
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(city__name__icontains=query)
            | Q(area__name__icontains=query)
        )

    # Budget filter — match against final price (discounted or original)
    if budget:
        qs = qs.filter(
            Q(discounted_price__isnull=False, discounted_price__lte=budget)
            | Q(discounted_price__isnull=True, price__lte=budget)
        )

    # Gender / hostel type filter
    if gender:
        GENDER_MAP = {
            "male": "boys",
            "female": "girls",
            "unisex": "co_living",
        }
        hostel_type = GENDER_MAP.get(gender, gender)
        qs = qs.filter(hostel_type=hostel_type)

    return qs.order_by("-rating_avg")
