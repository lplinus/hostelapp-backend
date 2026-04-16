"""
AI Context Builder — Converts filtered hostel querysets into compact, token-efficient text.

This module is responsible for building the minimal context string that gets
injected into the LLM prompt. It ensures we never exceed safe token limits.
"""

from hostels.models import Hostel
from locations.models import City

# ─── Configuration ────────────────────────────────────────────────────────────

MAX_HOSTELS_IN_CONTEXT = 6
MAX_CONTEXT_CHARS = 4000  # Keep prompt compact for free models


def format_price(val) -> str:
    """Convert a Decimal/float value to a clean ₹X,XXX string."""
    try:
        if not val:
            return "0"
        return "{:,.0f}".format(float(val))
    except (TypeError, ValueError):
        return "0"


def build_hostel_summary(hostel: Hostel) -> str:
    """
    Build a compact single-hostel summary string.
    Only includes essential fields to minimize token usage.
    """
    # Room types — compact format
    rooms = []
    for r in hostel.room_types.filter(is_available=True)[:4]:  # Max 4 room types
        rooms.append(
            f"{r.get_room_category_display()}/{r.get_sharing_type_display()}: ₹{format_price(r.base_price)}/mo"
        )

    # Amenities — just names, truncated
    amenities = [a.name for a in hostel.amenities.all()[:8]]  # Max 8 amenities

    # Build the compact entry
    lines = [
        f"• {hostel.name} ({hostel.get_hostel_type_display()})",
        f"  City: {hostel.city.name if hostel.city else 'N/A'}, Area: {hostel.area.name if hostel.area else 'N/A'}",
        f"  Price: ₹{format_price(hostel.price)}/mo",
    ]

    # Add discount if applicable
    if hostel.is_discounted and hostel.discounted_price:
        lines.append(f"  Discount: {hostel.discount_percentage}% off → ₹{format_price(hostel.discounted_price)}/mo")

    # Add rating if available
    if hostel.rating_avg and hostel.rating_avg > 0:
        lines.append(f"  Rating: {hostel.rating_avg}/5 ({hostel.rating_count} reviews)")

    if rooms:
        lines.append(f"  Rooms: {' | '.join(rooms)}")

    if amenities:
        lines.append(f"  Amenities: {', '.join(amenities)}")

    return "\n".join(lines)


def build_context(hostels, parsed_query: dict) -> str:
    """
    Build the complete context string from a filtered hostel queryset.

    Args:
        hostels: Filtered hostel queryset (already limited)
        parsed_query: Output from query_parser.parse_query()

    Returns:
        A compact context string ready for LLM injection
    """
    # Get available cities for general awareness
    all_cities = list(City.objects.values_list("name", flat=True))

    # Limit hostels
    hostel_list = list(hostels[:MAX_HOSTELS_IN_CONTEXT])
    total_count = hostels.count()

    # Build context parts
    parts = []

    # Header — brief platform info
    parts.append(f"HOSTEL IN PLATFORM — {total_count} hostels found")
    parts.append(f"Cities we serve: {', '.join(all_cities)}")
    parts.append("")

    if not hostel_list:
        parts.append("No hostels match the current search criteria.")
    else:
        # Show how many we're displaying vs total
        if total_count > MAX_HOSTELS_IN_CONTEXT:
            parts.append(f"Showing top {len(hostel_list)} of {total_count} matching hostels:")
        else:
            parts.append(f"Matching hostels ({len(hostel_list)}):")
        parts.append("")

        for hostel in hostel_list:
            summary = build_hostel_summary(hostel)
            parts.append(summary)
            parts.append("")

    context = "\n".join(parts)

    # Safety: truncate if somehow too long
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n...(more hostels available)"

    return context
