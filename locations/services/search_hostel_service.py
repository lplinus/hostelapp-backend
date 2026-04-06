from django.db.models import Q
from hostels.models import Hostel


def search_hostels(query: str = "", budget: int = None, gender: str = ""):
    """
    Search active hostels by name, city name, or area name.
    Optionally filter by budget (max price) and gender (hostel_type).
    """
    qs = (
        Hostel.objects.filter(is_active=True, is_approved=True)
        .select_related("area", "city")
        .prefetch_related("images", "room_types")
    )

    # Keywords mapping (e.g., "hyd" -> "Hyderabad")
    KEYWORD_MAPPINGS = {
        "hyd": "Hyderabad",
        "ben": "Bengaluru",
        "bang": "Bengaluru",
        "mum": "Mumbai",
        "che": "Chennai",
        "kol": "Kolkata",
        "viz": "Visakhapatnam",
        "del": "Delhi",
        "pun": "Pune",
        "gur": "Gurugram",
        "gurgaon": "Gurugram",
        "vzg": "Visakhapatnam",
        # Area mappings
        "kphb": "KPHB Colony",
        "sr nagar": "SR Nagar",
        "hsr": "HSR Layout",
        "btm": "BTM Layout",
    }

    # Text search across hostel name, city name, area name, and address
    if query:
        words = query.strip().split()
        mapped_words = [KEYWORD_MAPPINGS.get(w.lower(), w) for w in words]
        mapped_query = " ".join(mapped_words)

        qs = qs.filter(
            Q(name__icontains=mapped_query)
            | Q(city__name__icontains=mapped_query)
            | Q(area__name__icontains=mapped_query)
            | Q(address__icontains=mapped_query)
            | Q(name__icontains=query)  # Still match original query
            | Q(city__name__icontains=query)
            | Q(area__name__icontains=query)
            | Q(address__icontains=query)
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


def inner_search_hostels(query: str = "", city: str = "", hostel_type: str = "", room_type: str = "", sharing: str = ""):
    """
    Dedicated logic for inner hostel search (listing page).
    """
    qs = (
        Hostel.objects.filter(is_active=True, is_approved=True)
        .select_related("area", "city")
        .prefetch_related("images", "room_types")
    )

    KEYWORD_MAPPINGS = {
        "hyd": "Hyderabad",
        "ben": "Bengaluru",
        "bang": "Bengaluru",
        "mum": "Mumbai",
        "che": "Chennai",
        "kol": "Kolkata",
        "viz": "Visakhapatnam",
        "del": "Delhi",
        "pun": "Pune",
        "kphb": "KPHB Colony",
        "sr nagar": "SR Nagar",
        "hsr": "HSR Layout",
        "btm": "BTM Layout",
    }

    if query:
        words = query.strip().split()
        mapped_words = [KEYWORD_MAPPINGS.get(w.lower(), w) for w in words]
        mapped_query = " ".join(mapped_words)

        qs = qs.filter(
            Q(name__icontains=mapped_query)
            | Q(city__name__icontains=mapped_query)
            | Q(area__name__icontains=mapped_query)
            | Q(address__icontains=mapped_query)
            | Q(name__icontains=query)
            | Q(address__icontains=query)
        )

    if city and city != "All Cities":
        qs = qs.filter(city__name__iexact=city)

    if hostel_type and hostel_type != "all" and hostel_type != "All Types":
        qs = qs.filter(hostel_type=hostel_type)

    if room_type and room_type != "All Room Types":
        # Map frontend "Non-AC" to backend "NON_AC"
        backend_room_type = "NON_AC" if room_type == "Non-AC" else "AC"
        qs = qs.filter(room_types__room_category=backend_room_type).distinct()

    if sharing and sharing != "All Sharing Types":
        try:
            sharing_val = int(sharing)
            qs = qs.filter(room_types__sharing_type=sharing_val).distinct()
        except ValueError:
            pass

    return qs.order_by("-rating_avg")
