"""
AI Client — Handles all communication with Google Gemini API.

Uses the new `google.genai` SDK (replaces deprecated `google.generativeai`).
Encapsulates retry logic, fallback models, and structured logging.
"""

import time
import logging
from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger("ai.client")

# ─── Configuration ────────────────────────────────────────────────────────────

# (model_id, max_retries) — ordered by preference
# Primary: Gemini 2.5 Flash Lite | Fallback: Gemini 2.5 Flash
MODEL_PIPELINE = [
    ("gemini-2.5-flash-lite", 3),
    ("gemini-2.5-flash", 2),
]

DEFAULT_MAX_TOKENS = 512
DEFAULT_TEMPERATURE = 0.7


class AIClientError(Exception):
    """Raised when all models fail."""
    pass


def _extract_reply(response) -> str | None:
    """
    Safely extract text from a Gemini response.
    """
    try:
        # response.text is the simplest accessor in google.genai
        if response and response.text:
            return response.text.strip()

        # Fallback: check candidates manually
        if response and response.candidates:
            candidate = response.candidates[0]

            # Check finish reason for safety blocks
            finish_reason = getattr(candidate, "finish_reason", None)
            if finish_reason and str(finish_reason).upper() == "SAFETY":
                logger.warning("⚠️ Response blocked by safety filters.")
                return None

            # Try extracting from parts
            content = getattr(candidate, "content", None)
            if content and content.parts:
                text = "".join(
                    part.text for part in content.parts
                    if hasattr(part, "text") and part.text
                )
                return text.strip() if text.strip() else None

        return None
    except (ValueError, AttributeError, IndexError) as e:
        logger.warning(f"⚠️ Failed to extract reply: {e}")
        return None


def call_gemini_ai(system_prompt: str, user_message: str) -> str:
    """
    Send a chat completion request to Google Gemini with retry + fallback.

    Args:
        system_prompt: The system instruction (compact context included)
        user_message: The user's raw message

    Returns:
        The AI's reply text

    Raises:
        AIClientError: If all models and retries are exhausted
    """
    api_key = settings.GOOGLE_API_KEY
    if not api_key:
        raise AIClientError("GOOGLE_API_KEY is not configured in settings.")

    # Create a client instance with the API key
    client = genai.Client(api_key=api_key)

    # Log payload size for debugging
    total_prompt_chars = len(system_prompt) + len(user_message)
    logger.info(f"📤 Prompt size: {total_prompt_chars} chars")

    last_error = None

    for model_name, max_retries in MODEL_PIPELINE:
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🤖 Trying Gemini {model_name} (attempt {attempt}/{max_retries})")

                response = client.models.generate_content(
                    model=model_name,
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        max_output_tokens=DEFAULT_MAX_TOKENS,
                        temperature=DEFAULT_TEMPERATURE,
                    ),
                )

                # Safely extract reply text
                reply = _extract_reply(response)

                if reply:
                    logger.info(f"✅ Success with {model_name} ({len(reply)} chars)")
                    return reply
                else:
                    last_error = "Empty or blocked response from Gemini"
                    logger.warning(f"⚠️ {model_name}: {last_error}")
                    time.sleep(1)
                    continue

            except Exception as e:
                last_error = str(e)
                logger.warning(f"⚠️ {model_name}: Error — {last_error}")

                # If it's a safety/blocked error, skip remaining retries for this model
                if "block" in last_error.lower() or "safety" in last_error.lower():
                    logger.error(f"❌ {model_name}: Content blocked by safety filters.")
                    break

                time.sleep(1 * attempt)  # Simple backoff
                continue

    # All models exhausted
    logger.error(f"❌ All Gemini models failed. Last error: {last_error}")
    raise AIClientError(f"All Gemini models failed. Last error: {last_error}")

