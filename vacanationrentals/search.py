import re
from django.db.models import Q
from locations.models import City, Area
from .models import VacationRental

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
    "lonavala": "Lonavala",
    "khandala": "Khandala",
    "alibaug": "Alibaug",
}

# Vacation rental category synonyms
CATEGORY_SYNONYMS = {
    "villa": VacationRental.PropertyCategory.VILLA,
    "villas": VacationRental.PropertyCategory.VILLA,
    "beach house": VacationRental.PropertyCategory.BEACH_HOUSE,
    "beachhouse": VacationRental.PropertyCategory.BEACH_HOUSE,
    "beach villa": VacationRental.PropertyCategory.BEACH_HOUSE,
    "oceanfront": VacationRental.PropertyCategory.BEACH_HOUSE,
    "cabin": VacationRental.PropertyCategory.CABIN,
    "cabins": VacationRental.PropertyCategory.CABIN,
    "chalet": VacationRental.PropertyCategory.CABIN,
    "farmhouse": VacationRental.PropertyCategory.FARMHOUSE,
    "farm house": VacationRental.PropertyCategory.FARMHOUSE,
    "farmstay": VacationRental.PropertyCategory.FARMHOUSE,
    "farm": VacationRental.PropertyCategory.FARMHOUSE,
    "cottage": VacationRental.PropertyCategory.COTTAGE,
    "cottages": VacationRental.PropertyCategory.COTTAGE,
    "penthouse": VacationRental.PropertyCategory.PENTHOUSE,
    "penthouses": VacationRental.PropertyCategory.PENTHOUSE,
    "apartment": VacationRental.PropertyCategory.APARTMENT,
    "apartments": VacationRental.PropertyCategory.APARTMENT,
    "flat": VacationRental.PropertyCategory.APARTMENT,
    "flats": VacationRental.PropertyCategory.APARTMENT,
    "condo": VacationRental.PropertyCategory.APARTMENT,
    "house": VacationRental.PropertyCategory.HOUSE,
    "houses": VacationRental.PropertyCategory.HOUSE,
    "bungalow": VacationRental.PropertyCategory.HOUSE,
    "homestay": VacationRental.PropertyCategory.HOUSE,
    "studio": VacationRental.PropertyCategory.STUDIO,
}

# Stop words to ignore during token extraction
STOP_WORDS = {
    "vacation", "rentals", "rental", "stay", "stays", "in", "near", "at",
    "around", "of", "the", "a", "an", "and", "or", "for", "with", "to",
    "from", "by", "best", "top", "good", "find", "search", "looking",
    "want", "need", "place", "places", "home", "homes", "property",
    "properties", "book", "reserve"
}


def search_vacation_rentals(queryset, query_str: str):
    """
    Intelligent natural-language search engine for Vacation Rentals.
    Parses user queries like 'villas in goa', 'beach house in pondicherry',
    'penthouse in hyderabad', or 'mountain cabin in bangalore'.
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
        Q(title__icontains=raw_query)
        | Q(city__name__icontains=raw_query)
        | Q(area__name__icontains=raw_query)
        | Q(address__icontains=raw_query)
        | Q(tagline__icontains=raw_query)
    )
    direct_results = queryset.filter(direct_match_q).distinct()
    if direct_results.exists():
        title_or_tagline_matches = queryset.filter(
            Q(title__icontains=raw_query) | Q(tagline__icontains=raw_query)
        ).distinct()
        if title_or_tagline_matches.exists():
            return title_or_tagline_matches

    # 2. Extract Property Category intent (multi-word like 'beach house' first)
    detected_category = None
    sorted_cat_synonyms = sorted(CATEGORY_SYNONYMS.keys(), key=lambda x: len(x), reverse=True)
    for cat_syn in sorted_cat_synonyms:
        pattern = rf"\b{re.escape(cat_syn)}\b"
        if re.search(pattern, clean_query):
            detected_category = CATEGORY_SYNONYMS[cat_syn]
            clean_query = re.sub(pattern, " ", clean_query)
            break

    # 3. Extract City & Location intent
    detected_city_name = None
    sorted_city_aliases = sorted(CITY_KEYWORD_MAPPINGS.keys(), key=lambda x: len(x), reverse=True)
    for alias in sorted_city_aliases:
        pattern = rf"\b{re.escape(alias)}\b"
        if re.search(pattern, clean_query):
            detected_city_name = CITY_KEYWORD_MAPPINGS[alias]
            clean_query = re.sub(pattern, " ", clean_query)
            break

    # Also check existing cities in the database dynamically
    if not detected_city_name:
        db_cities = City.objects.filter(is_deleted=False).values_list("name", flat=True)
        for city_name in sorted(db_cities, key=lambda x: len(x), reverse=True):
            if re.search(rf"\b{re.escape(city_name.lower())}\b", clean_query):
                detected_city_name = city_name
                clean_query = re.sub(rf"\b{re.escape(city_name.lower())}\b", " ", clean_query)
                break

    # 4. Extract Amenities / Feature intent
    feature_filters = []
    if re.search(r"\b(pool|private pool|swimming pool)\b", clean_query):
        feature_filters.append("pool")
        clean_query = re.sub(r"\b(pool|private pool|swimming pool)\b", " ", clean_query)
    if re.search(r"\b(pet|pets|pet friendly)\b", clean_query):
        feature_filters.append("pet")
        clean_query = re.sub(r"\b(pet|pets|pet friendly)\b", " ", clean_query)
    if re.search(r"\b(superhost|super host)\b", clean_query):
        feature_filters.append("superhost")
        clean_query = re.sub(r"\b(superhost|super host)\b", " ", clean_query)
    if re.search(r"\b(instant book|instant)\b", clean_query):
        feature_filters.append("instant")
        clean_query = re.sub(r"\b(instant book|instant)\b", " ", clean_query)

    # 5. Extract Bedrooms intent (e.g. 2 bhk, 3 bedroom, 4 bedrooms)
    detected_bedrooms = None
    bhk_match = re.search(r"\b(\d+)\s*(bhk|bedroom|bedrooms|bed)\b", clean_query)
    if bhk_match:
        try:
            detected_bedrooms = int(bhk_match.group(1))
            clean_query = re.sub(r"\b(\d+)\s*(bhk|bedroom|bedrooms|bed)\b", " ", clean_query)
        except ValueError:
            pass

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

    if detected_category:
        q_filter &= Q(category=detected_category)

    if detected_bedrooms:
        q_filter &= Q(bedrooms__gte=detected_bedrooms)

    if "pet" in feature_filters:
        q_filter &= Q(allows_pets=True)

    if "superhost" in feature_filters:
        q_filter &= Q(is_superhost=True)

    if "instant" in feature_filters:
        q_filter &= Q(instant_book=True)

    if "pool" in feature_filters:
        q_filter &= (
            Q(amenities__name__icontains="pool")
            | Q(title__icontains="pool")
            | Q(tagline__icontains="pool")
        )

    # Match remaining words across title, area, tagline, address, description
    for token in remaining_tokens:
        token_q = (
            Q(title__icontains=token)
            | Q(area__name__icontains=token)
            | Q(tagline__icontains=token)
            | Q(address__icontains=token)
            | Q(description__icontains=token)
        )
        q_filter &= token_q

    # Execute search
    results = queryset.filter(q_filter).distinct()

    # If strict AND query returned nothing, relax criteria gracefully
    if not results.exists() and (detected_city_name or remaining_tokens or detected_category):
        relaxed_q = Q()
        if detected_city_name:
            relaxed_q |= Q(city__name__icontains=detected_city_name)
        if detected_category:
            relaxed_q |= Q(category=detected_category)
        for token in remaining_tokens:
            relaxed_q |= Q(title__icontains=token) | Q(area__name__icontains=token) | Q(tagline__icontains=token)

        results = queryset.filter(relaxed_q).distinct()

    # Fallback to direct match if still empty
    if not results.exists():
        results = direct_results

    return results
