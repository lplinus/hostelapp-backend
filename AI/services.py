"""
AI Chat Service — Orchestrator layer.

This is the core business logic layer that coordinates:
  Query Parser → Database Filter → Context Builder → AI Client → Response

No framework-specific code here (no Request/Response objects).
"""

import logging
from django.db.models import Q
from hostels.models import Hostel
from .query_parser import parse_query
from .context_builder import build_context
from .ai_client import call_openrouter, AIClientError

logger = logging.getLogger("ai.service")

# ─── Configuration ────────────────────────────────────────────────────────────

MAX_RESULTS = 7  # Maximum hostels to fetch from DB


# ─── System prompt (kept SHORT and structured) ────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """You are 'Hostel In AI' — a concise, friendly hostel assistant for India.

DATA:
{context}

RULES:
- Answer ONLY from the data above. Never invent hostels or prices.
- Prices: always format as ₹X,XXX/month (no decimals).
- Keep answers short: 2-5 sentences. Use bullet points for lists.
- If no matching hostel found, say "We're expanding there! Check our available cities."
- For booking: "Visit the hostel page and click Book Now."
- For support/complaints: "Contact us on WhatsApp at 9392356996."
- Do NOT use markdown formatting (no **, ##, etc). Plain text only."""


class AIChatService:
    """
    Main service class that handles the complete chat flow.
    Stateless — each call is independent.
    """

    @staticmethod
    def get_response(user_message: str) -> dict:
        """
        Process a user message and return an AI response.

        Args:
            user_message: The raw text from the user

        Returns:
            {"reply": str, "status": "success"} on success
            {"error": str, "status": "failed"} on failure
        """
        try:
            # ── Step 1: Parse the user's query ────────────────────────────
            parsed = parse_query(user_message)
            logger.info(
                f"🔍 Parsed: intent={parsed['intent']}, "
                f"cities={parsed['cities']}, "
                f"type={parsed['hostel_type']}, "
                f"price={parsed['price_range']}, "
                f"amenities={parsed['amenity_keywords']}"
            )

            # ── Step 2: Handle non-data intents early ─────────────────────
            if parsed["intent"] == "greeting":
                return {
                    "reply": (
                        "Hey there! Welcome to Hostel In! 🏠\n"
                        "I can help you find hostels across India.\n"
                        "Try asking me:\n"
                        "- Hostels in Hyderabad\n"
                        "- Budget hostels under ₹5,000\n"
                        "- Boys PG with WiFi"
                    ),
                    "status": "success",
                }

            if parsed["intent"] == "support":
                return {
                    "reply": (
                        "Need help? We're here for you!\n"
                        "- WhatsApp: 9392356996\n"
                        "- You can also reach us through the Contact Us page.\n"
                        "Our team typically responds within a few hours."
                    ),
                    "status": "success",
                }

            if parsed["intent"] == "booking":
                return {
                    "reply": (
                        "Booking is easy!\n"
                        "1. Browse hostels on our website\n"
                        "2. Click on a hostel you like\n"
                        "3. Select your room type\n"
                        "4. Click 'Book Now' and complete payment\n"
                        "Need help finding a hostel? Just ask!"
                    ),
                    "status": "success",
                }

            # ── Step 3: Filter hostels from database ──────────────────────
            hostels = AIChatService._filter_hostels(parsed)

            # ── Step 4: Build compact context ─────────────────────────────
            context = build_context(hostels, parsed)
            logger.info(f"📦 Context built: {len(context)} chars")

            # ── Step 5: Build system prompt ───────────────────────────────
            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

            # ── Step 6: Call AI ───────────────────────────────────────────
            reply = call_openrouter(system_prompt, user_message)

            return {
                "reply": reply,
                "status": "success",
            }

        except AIClientError as e:
            logger.error(f"❌ AI Client Error: {e}")
            return {
                "error": "The AI assistant is temporarily unavailable. Please try again in a moment.",
                "details": str(e),
                "status": "failed",
            }

        except Exception as e:
            logger.error(f"❌ Unexpected service error: {e}", exc_info=True)
            return {
                "error": "Something went wrong. Please try again.",
                "details": str(e),
                "status": "failed",
            }

    @staticmethod
    def _filter_hostels(parsed: dict):
        """
        Apply smart filters to the Hostel queryset based on parsed query.
        Returns a queryset limited to MAX_RESULTS.
        """
        qs = Hostel.objects.filter(
            is_active=True,
            is_approved=True,
        ).select_related("city", "area").prefetch_related(
            "amenities",
            "room_types",
        )

        # ── City filter ───────────────────────────────────────────────────
        if parsed["city_ids"]:
            qs = qs.filter(city_id__in=parsed["city_ids"])

        # ── Area filter ───────────────────────────────────────────────────
        if parsed["area_ids"]:
            qs = qs.filter(area_id__in=parsed["area_ids"])

        # ── Hostel type filter ────────────────────────────────────────────
        if parsed["hostel_type"]:
            qs = qs.filter(hostel_type=parsed["hostel_type"])

        # ── Price range filter ────────────────────────────────────────────
        if parsed["price_range"]:
            min_price, max_price = parsed["price_range"]
            qs = qs.filter(price__gte=min_price, price__lte=max_price)

        # ── Amenity keyword filter ────────────────────────────────────────
        if parsed["amenity_keywords"]:
            amenity_q = Q()
            for keyword in parsed["amenity_keywords"]:
                amenity_q |= Q(amenities__name__icontains=keyword)
            qs = qs.filter(amenity_q).distinct()

        # ── Ordering: prioritize featured, verified, then by price ────────
        qs = qs.order_by("-is_featured", "-is_verified", "price")

        # ── Limit results ─────────────────────────────────────────────────
        return qs[:MAX_RESULTS]
