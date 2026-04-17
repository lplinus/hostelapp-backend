"""
AI Hashing Utility — Generates a deterministic hash of key hostel fields.

Used for change detection: if the hash matches the stored value,
the AI description is still valid and no API call is needed.
"""

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hostels.models import Hostel


# Current prompt version — increment this to force regeneration across all hostels
CURRENT_AI_VERSION: int = 1


def compute_hostel_hash(hostel: "Hostel") -> str:
    """
    Generate an MD5 hash from the hostel's content-significant fields.

    Only fields that materially affect the AI-generated description are
    included. Cosmetic or operational fields (is_active, is_featured,
    rating, images, etc.) are intentionally excluded.

    Args:
        hostel: A Hostel model instance (city/area must be select_related).

    Returns:
        A 32-character hexadecimal MD5 digest string.
    """
    # ── Gather field values ───────────────────────────────────────────────
    parts: list[str] = [
        hostel.name or "",
        hostel.description or "",
        hostel.short_description or "",
        hostel.hostel_type or "",
        hostel.address or "",
        hostel.city.name if hostel.city_id and hostel.city else "",
        hostel.area.name if hostel.area_id and hostel.area else "",
    ]

    # Amenities — sorted for determinism (M2M order is not guaranteed)
    amenity_names: list[str] = sorted(
        hostel.amenities.values_list("name", flat=True)
    )
    parts.append(",".join(amenity_names))

    # Price (as string for hashing)
    parts.append(str(hostel.price or ""))

    # Include prompt version so bumping it invalidates all cached hashes
    parts.append(str(CURRENT_AI_VERSION))

    # ── Build hash ────────────────────────────────────────────────────────
    raw = "|".join(parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
