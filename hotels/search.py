import re
from django.db.models import Q
from locations.models import City, Area
from .models import Hotel

# City abbreviation & nickname mappings
CITY_KEYWORD_MAPPINGS = {
    "hyd": "Hyderabad",
    "hyderabad": "Hyderabad",
    "secunderabad": "Hyderabad",
    "blr": "Bengaluru",
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "mum": "Mumbai",
    "bombay": "Mumbai",
    "mumbai": "Mumbai",
    "navi mumbai": "Mumbai",
    "del": "Delhi",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "ncr": "Delhi",
    "pun": "Pune",
    "pune": "Pune",
    "che": "Chennai",
    "madras": "Chennai",
    "chennai": "Chennai",
    "goa": "Goa",
    "north goa": "Goa",
    "south goa": "Goa",
    "panaji": "Panaji",
    "jai": "Jaipur",
    "jaipur": "Jaipur",
    "udr": "Udaipur",
    "udaipur": "Udaipur",
    "koc": "Kochi",
    "cochin": "Kochi",
    "kochi": "Kochi",
    "kol": "Kolkata",
    "calcutta": "Kolkata",
    "kolkata": "Kolkata",
    "viz": "Visakhapatnam",
    "vizag": "Visakhapatnam",
    "visakhapatnam": "Visakhapatnam",
    "pondicherry": "Pondicherry",
    "puducherry": "Pondicherry",
    "hampi": "Hampi",
    "manali": "Manali",
    "shimla": "Shimla",
    "ooty": "Ooty",
}

# Hotel type synonyms
HOTEL_TYPE_SYNONYMS = {
    "luxury": Hotel.HotelType.LUXURY,
    "lux": Hotel.HotelType.LUXURY,
    "5-star": Hotel.HotelType.LUXURY,
    "boutique": Hotel.HotelType.BOUTIQUE,
    "business": Hotel.HotelType.BUSINESS,
    "corporate": Hotel.HotelType.BUSINESS,
    "resort": Hotel.HotelType.RESORT,
    "spa": Hotel.HotelType.RESORT,
    "heritage": Hotel.HotelType.HERITAGE,
    "palace": Hotel.HotelType.HERITAGE,
    "haveli": Hotel.HotelType.HERITAGE,
    "budget": Hotel.HotelType.BUDGET,
    "affordable": Hotel.HotelType.BUDGET,
    "cheap": Hotel.HotelType.BUDGET,
}

# Stop words and connective terms to ignore when extracting entities
STOP_WORDS = {
    "hotel", "hotels", "stay", "stays", "in", "near", "at", "around",
    "of", "the", "a", "an", "and", "or", "for", "with", "to", "from",
    "by", "best", "top", "good", "find", "search", "looking", "want",
    "need", "place", "places", "room", "rooms", "suite", "suites",
    "accommodation", "accommodations", "resort", "resorts"
}


def search_hotels(queryset, query_str: str):
    """
    Intelligent natural-language search engine for hotels.
    Parses user queries like 'hotels in hyderabad', '5 star hotels in mumbai',
    'luxury resort in goa', or 'marriott banjara hills'.
    """
    if not query_str or not str(query_str).strip():
        return queryset

    raw_query = str(query_str).strip()
    clean_query = re.sub(r"[^\w\s-]", " ", raw_query.lower())
    clean_query = re.sub(r"\s+", " ", clean_query).strip()

    if not clean_query:
        return queryset

    # 1. Exact direct match fallback (e.g. search for full property title)
    direct_match_q = (
        Q(name__icontains=raw_query)
        | Q(city__name__icontains=raw_query)
        | Q(area__name__icontains=raw_query)
        | Q(address__icontains=raw_query)
        | Q(tagline__icontains=raw_query)
    )
    direct_results = queryset.filter(direct_match_q).distinct()
    if direct_results.exists():
        # If user typed an exact hotel name like "Lake Pichola Grand", direct match is highly accurate
        # We check if direct match returned more than just a generic match
        # If it returned high-confidence name/tagline match, return it
        name_or_tagline_matches = queryset.filter(
            Q(name__icontains=raw_query) | Q(tagline__icontains=raw_query)
        ).distinct()
        if name_or_tagline_matches.exists():
            return name_or_tagline_matches

    # 2. Extract Star Rating intent
    detected_star_rating = None
    star_patterns = [
        (r"\b(5|five)\s*(-|\s)?\s*star\b", 5),
        (r"\b(4|four)\s*(-|\s)?\s*star\b", 4),
        (r"\b(3|three)\s*(-|\s)?\s*star\b", 3),
        (r"\b(7|seven)\s*(-|\s)?\s*star\b", 5), # Often used colloquially for ultra-luxury
    ]
    for pattern, rating in star_patterns:
        if re.search(pattern, clean_query):
            detected_star_rating = rating
            clean_query = re.sub(pattern, " ", clean_query)
            break

    # 3. Extract Hotel Type intent
    detected_hotel_type = None
    for token, htype in HOTEL_TYPE_SYNONYMS.items():
        # Check whole word match
        if re.search(rf"\b{re.escape(token)}\b", clean_query):
            detected_hotel_type = htype
            clean_query = re.sub(rf"\b{re.escape(token)}\b", " ", clean_query)
            break

    # 4. Extract City & Location intent
    detected_city_name = None
    # Check multi-word cities first (e.g. "navi mumbai", "new delhi", "south goa")
    sorted_city_aliases = sorted(CITY_KEYWORD_MAPPINGS.keys(), key=lambda x: len(x), reverse=True)
    for alias in sorted_city_aliases:
        pattern = rf"\b{re.escape(alias)}\b"
        if re.search(pattern, clean_query):
            detected_city_name = CITY_KEYWORD_MAPPINGS[alias]
            clean_query = re.sub(pattern, " ", clean_query)
            break

    # Also check existing cities in the database dynamically if not caught by aliases
    if not detected_city_name:
        db_cities = City.objects.filter(is_deleted=False).values_list("name", flat=True)
        for city_name in sorted(db_cities, key=lambda x: len(x), reverse=True):
            if re.search(rf"\b{re.escape(city_name.lower())}\b", clean_query):
                detected_city_name = city_name
                clean_query = re.sub(rf"\b{re.escape(city_name.lower())}\b", " ", clean_query)
                break

    # 5. Extract Amenities intent (e.g. pool, pet friendly)
    amenity_filters = []
    if re.search(r"\b(pool|swimming pool)\b", clean_query):
        amenity_filters.append("pool")
        clean_query = re.sub(r"\b(pool|swimming pool)\b", " ", clean_query)
    if re.search(r"\b(pet|pets|pet friendly)\b", clean_query):
        amenity_filters.append("pet")
        clean_query = re.sub(r"\b(pet|pets|pet friendly)\b", " ", clean_query)

    # 6. Extract Remaining Content Tokens
    words = re.findall(r"\b\w+\b", clean_query)
    remaining_tokens = [w for w in words if w not in STOP_WORDS and len(w) > 1]

    # 7. Construct Targeted Query
    q_filter = Q()

    if detected_city_name:
        q_filter &= (
            Q(city__name__icontains=detected_city_name)
            | Q(city__slug__icontains=detected_city_name.lower())
            | Q(address__icontains=detected_city_name)
        )

    if detected_star_rating:
        q_filter &= Q(star_rating__gte=detected_star_rating)

    if detected_hotel_type:
        q_filter &= Q(hotel_type=detected_hotel_type)

    if "pet" in amenity_filters:
        q_filter &= Q(allows_pets=True)

    if "pool" in amenity_filters:
        q_filter &= Q(amenities__name__icontains="pool")

    # Match remaining words across name, area, tagline, address
    for token in remaining_tokens:
        token_q = (
            Q(name__icontains=token)
            | Q(area__name__icontains=token)
            | Q(tagline__icontains=token)
            | Q(address__icontains=token)
            | Q(description__icontains=token)
        )
        q_filter &= token_q

    # Execute search
    results = queryset.filter(q_filter).distinct()

    # If strict AND query returned nothing, relax criteria gracefully
    if not results.exists() and (detected_city_name or remaining_tokens):
        relaxed_q = Q()
        if detected_city_name:
            relaxed_q |= Q(city__name__icontains=detected_city_name)
        for token in remaining_tokens:
            relaxed_q |= Q(name__icontains=token) | Q(area__name__icontains=token) | Q(tagline__icontains=token)

        results = queryset.filter(relaxed_q).distinct()

    # Fallback to direct match if still empty
    if not results.exists():
        results = direct_results

    return results
