"""
Hostel AI Service — Orchestrates AI description generation with caching.

Core Logic:
  1. Compute hash of current hostel data
  2. If hash matches stored ai_hash → return cached ai_description (NO API call)
  3. If hash differs → call Gemini API → persist result → return new description

This service is the ONLY entry point for AI description generation.
Views and signals must NEVER call the AI directly.
"""

import logging
from datetime import timezone, datetime
from typing import TYPE_CHECKING

from .hashing import compute_hostel_hash, CURRENT_AI_VERSION
from .ai_client import call_gemini_ai, AIClientError

if TYPE_CHECKING:
    from hostels.models import Hostel

logger = logging.getLogger("ai.service")


# ─── Prompt Template ──────────────────────────────────────────────────────────

DESCRIPTION_PROMPT: str = """You are a professional hostel copywriter for the Indian market.

Write a compelling, SEO-friendly marketing description for this hostel.

HOSTEL DATA:
- Name: {name}
- Type: {hostel_type}
- City: {city}, Area: {area}
- Address: {address}
- Starting Price: ₹{price}/month
- Amenities: {amenities}
- Short Description: {short_description}

RULES:
- Write 3-4 paragraphs (150-250 words total).
- Highlight location advantages, amenities, and value for money.
- Use natural, engaging language — not robotic.
- Include relevant keywords for SEO (hostel, PG, accommodation, the city name).
- Do NOT use markdown formatting (no **, ##, etc). Plain text only.
- Do NOT invent amenities or features not listed above.
- Write in third person."""

FALLBACK_DESCRIPTION: str = (
    "Welcome to this well-maintained hostel offering comfortable "
    "accommodation with modern amenities. Conveniently located with "
    "easy access to key landmarks, it provides an ideal living "
    "experience for students and working professionals alike."
)


class HostelAIService:
    """
    Stateless service for AI-powered hostel description generation.
    Implements hash-based caching to avoid redundant API calls.
    """

    @staticmethod
    def generate_description(hostel: "Hostel") -> str:
        """
        Generate (or return cached) AI description for a hostel.

        Args:
            hostel: Hostel instance with city/area select_related
                    and amenities prefetch_related.

        Returns:
            The AI-generated description string.
        """
        # ── Step 1: Compute current hash ──────────────────────────────────
        current_hash: str = compute_hostel_hash(hostel)

        # ── Step 2: Check cache ───────────────────────────────────────────
        if (
            hostel.ai_hash == current_hash
            and hostel.ai_description
            and hostel.ai_version == CURRENT_AI_VERSION
        ):
            logger.info(f"✅ Cache HIT for '{hostel.name}' (hash={current_hash[:8]}…)")
            return hostel.ai_description

        logger.info(f"🔄 Cache MISS for '{hostel.name}' — generating new description…")

        # ── Step 3: Build prompt ──────────────────────────────────────────
        amenity_names: list[str] = list(
            hostel.amenities.values_list("name", flat=True)
        )

        prompt: str = DESCRIPTION_PROMPT.format(
            name=hostel.name,
            hostel_type=hostel.get_hostel_type_display(),
            city=hostel.city.name if hostel.city_id else "N/A",
            area=hostel.area.name if hostel.area_id else "N/A",
            address=hostel.address or "N/A",
            price="{:,.0f}".format(float(hostel.price)) if hostel.price else "N/A",
            amenities=", ".join(amenity_names) if amenity_names else "N/A",
            short_description=hostel.short_description or "N/A",
        )

        # ── Step 4: Call Gemini API ───────────────────────────────────────
        try:
            description: str = call_gemini_ai(
                system_prompt="You are a professional hostel copywriter.",
                user_message=prompt,
            )
        except AIClientError as e:
            logger.error(f"❌ AI generation failed for '{hostel.name}': {e}")
            description = FALLBACK_DESCRIPTION

        # ── Step 5: Persist to DB ─────────────────────────────────────────
        hostel.ai_description = description
        hostel.ai_hash = current_hash
        hostel.ai_generated_at = datetime.now(tz=timezone.utc)
        hostel.ai_version = CURRENT_AI_VERSION

        hostel.save(
            update_fields=[
                "ai_description",
                "ai_hash",
                "ai_generated_at",
                "ai_version",
            ]
        )

        logger.info(
            f"✅ AI description saved for '{hostel.name}' "
            f"({len(description)} chars, hash={current_hash[:8]}…)"
        )

        return description

    @staticmethod
    def invalidate(hostel: "Hostel") -> None:
        """
        Mark a hostel's AI cache as stale by clearing the hash.
        Does NOT call the AI — that happens lazily or via management command.

        Args:
            hostel: Hostel instance to invalidate.
        """
        if hostel.ai_hash is not None:
            hostel.ai_hash = None
            hostel.save(update_fields=["ai_hash"])
            logger.info(f"🗑️ AI cache invalidated for '{hostel.name}'")
