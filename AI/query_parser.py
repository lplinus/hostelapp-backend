"""
AI Query Parser — Extracts intent, filters, and keywords from user messages.

Performs lightweight NLP (keyword matching) to understand what the user is asking,
so we only fetch relevant hostels from the database instead of sending everything.
"""

import re
from locations.models import City, Area


# ─── Keyword dictionaries for intent detection ────────────────────────────────

HOSTEL_TYPE_MAP = {
    # keyword → DB value
    "boys": "boys",
    "boy": "boys",
    "male": "boys",
    "men": "boys",
    "girls": "girls",
    "girl": "girls",
    "female": "girls",
    "women": "girls",
    "co-living": "co_living",
    "coliving": "co_living",
    "co living": "co_living",
    "coed": "co_living",
    "co-ed": "co_living",
    "working professional": "working_professional",
    "working professionals": "working_professional",
    "professional": "working_professional",
    "student": "student",
    "students": "student",
    "luxury": "luxury",
    "premium": "luxury",
    "budget": "budget",
    "cheap": "budget",
    "affordable": "budget",
    "low cost": "budget",
    "low price": "budget",
    "pg": "pg",
    "paying guest": "pg",
}

AMENITY_KEYWORDS = [
    "wifi", "wi-fi", "internet",
    "ac", "air conditioning", "air conditioner",
    "food", "mess", "meals", "breakfast", "lunch", "dinner", "tiffin",
    "laundry", "washing",
    "gym", "fitness",
    "parking",
    "cctv", "security",
    "power backup", "generator",
    "hot water", "geyser",
    "tv", "television",
    "fridge", "refrigerator",
    "study room", "study area", "library",
]

PRICE_KEYWORDS = {
    "cheap": (0, 4000),
    "budget": (0, 4000),
    "affordable": (0, 5000),
    "low cost": (0, 4000),
    "low price": (0, 4000),
    "mid range": (4000, 7000),
    "moderate": (4000, 7000),
    "premium": (7000, 50000),
    "luxury": (7000, 50000),
    "expensive": (7000, 50000),
}

INTENT_PATTERNS = {
    "list_hostels": [
        r"(?:show|list|find|search|get|see|available|all)\s.*hostel",
        r"hostel(?:s)?\s.*(?:in|at|near|around)",
        r"what\s.*hostel",
        r"any\s.*hostel",
        r"which\s.*hostel",
    ],
    "pricing": [
        r"(?:price|pricing|cost|rate|fee|charge|rent|how much)",
        r"(?:cheap|budget|affordable|expensive)",
        r"₹|\brs\b|\brupee",
    ],
    "booking": [
        r"(?:book|reserve|booking|reservation)",
        r"how\s.*(?:book|reserve)",
    ],
    "amenities": [
        r"(?:amenity|amenities|facility|facilities|feature|features)",
        r"(?:wifi|ac|food|gym|laundry|parking|cctv|power backup)",
    ],
    "support": [
        r"(?:help|support|contact|complaint|issue|problem|whatsapp|call)",
    ],
    "greeting": [
        r"^(?:hi|hello|hey|hii|good morning|good evening|howdy)",
    ],
}


def parse_query(message: str) -> dict:
    """
    Parses a user message and returns structured query parameters.

    Returns:
        {
            "intent": str,            # list_hostels, pricing, booking, amenities, support, greeting, general
            "cities": [str],          # list of matched city names
            "city_ids": [int],        # list of matched city IDs
            "areas": [str],           # list of matched area names
            "area_ids": [int],        # list of matched area IDs
            "hostel_type": str|None,  # matched hostel type DB value
            "price_range": (min, max)|None,
            "amenity_keywords": [str],
            "raw_message": str,
        }
    """
    msg_lower = message.lower().strip()

    result = {
        "intent": "general",
        "cities": [],
        "city_ids": [],
        "areas": [],
        "area_ids": [],
        "hostel_type": None,
        "price_range": None,
        "amenity_keywords": [],
        "raw_message": message,
    }

    # ── 1. Detect intent ──────────────────────────────────────────────────
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, msg_lower):
                result["intent"] = intent
                break
        if result["intent"] != "general":
            break

    # ── 2. Detect cities ──────────────────────────────────────────────────
    all_cities = City.objects.values_list("id", "name")
    for cid, cname in all_cities:
        if cname.lower() in msg_lower:
            result["cities"].append(cname)
            result["city_ids"].append(cid)

    # ── 3. Detect areas ───────────────────────────────────────────────────
    all_areas = Area.objects.values_list("id", "name")
    for aid, aname in all_areas:
        if aname.lower() in msg_lower:
            result["areas"].append(aname)
            result["area_ids"].append(aid)

    # ── 4. Detect hostel type ─────────────────────────────────────────────
    for keyword, db_value in HOSTEL_TYPE_MAP.items():
        if keyword in msg_lower:
            result["hostel_type"] = db_value
            break

    # ── 5. Detect price range ─────────────────────────────────────────────
    # Check explicit amounts: "under 5000", "below 3000", "5000-8000"
    range_match = re.search(r"(\d{3,6})\s*(?:to|-)\s*(\d{3,6})", msg_lower)
    if range_match:
        result["price_range"] = (int(range_match.group(1)), int(range_match.group(2)))
    else:
        under_match = re.search(r"(?:under|below|less than|within)\s*₹?\s*(\d{3,6})", msg_lower)
        if under_match:
            result["price_range"] = (0, int(under_match.group(1)))
        else:
            above_match = re.search(r"(?:above|over|more than|starting)\s*₹?\s*(\d{3,6})", msg_lower)
            if above_match:
                result["price_range"] = (int(above_match.group(1)), 100000)
            else:
                # Check keyword-based price hints
                for keyword, price_range in PRICE_KEYWORDS.items():
                    if keyword in msg_lower:
                        result["price_range"] = price_range
                        break

    # ── 6. Detect amenity keywords ────────────────────────────────────────
    for keyword in AMENITY_KEYWORDS:
        if keyword in msg_lower:
            result["amenity_keywords"].append(keyword)

    return result
