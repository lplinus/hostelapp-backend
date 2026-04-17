"""
Hostel Signals — Invalidates AI cache when hostel data changes.

IMPORTANT:
  - Signals only INVALIDATE (set ai_hash = null).
  - They do NOT call the AI API.
  - AI generation happens via the management command or explicit service call.
"""

import logging
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver

from .models import Hostel

logger = logging.getLogger("ai.service")


@receiver(post_save, sender=Hostel)
def invalidate_ai_on_hostel_save(
    sender: type,
    instance: Hostel,
    created: bool,
    update_fields: frozenset | None = None,
    **kwargs,
) -> None:
    """
    After a hostel is created or updated, invalidate the AI cache
    UNLESS the save was triggered by the AI service itself
    (detected via update_fields containing only AI fields).
    """
    # Skip if this save came from HostelAIService (only AI fields updated)
    ai_only_fields = {"ai_description", "ai_hash", "ai_generated_at", "ai_version"}
    if update_fields and set(update_fields).issubset(ai_only_fields):
        return

    # Skip price-only updates from update_price_from_rooms
    price_only_fields = {"price", "price_per_day"}
    if update_fields and set(update_fields).issubset(price_only_fields):
        return

    # Invalidate: set ai_hash to null so next generation picks up changes
    if instance.ai_hash is not None:
        Hostel.objects.filter(pk=instance.pk).update(ai_hash=None)
        logger.info(f"🔄 AI cache invalidated for '{instance.name}' (post_save)")


@receiver(m2m_changed, sender=Hostel.amenities.through)
def invalidate_ai_on_amenity_change(
    sender: type,
    instance: Hostel,
    action: str,
    **kwargs,
) -> None:
    """
    Invalidate AI cache when hostel amenities change.
    Only fires on actual data mutations, not pre-clear/pre-add signals.
    """
    if action in ("post_add", "post_remove", "post_clear"):
        if instance.ai_hash is not None:
            Hostel.objects.filter(pk=instance.pk).update(ai_hash=None)
            logger.info(
                f"🔄 AI cache invalidated for '{instance.name}' (amenities changed)"
            )
