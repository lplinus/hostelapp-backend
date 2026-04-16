"""
AI Client — Handles all communication with OpenRouter API.

Encapsulates retry logic, fallback models, timeout handling,
and structured logging for production debugging.
"""

import time
import logging
import requests as http_requests
from django.conf import settings

logger = logging.getLogger("ai.client")

# ─── Configuration ────────────────────────────────────────────────────────────

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# (model_id, max_retries) — ordered by preference
MODEL_PIPELINE = [
    ("openrouter/free", 3),
    ("meta-llama/llama-3.3-70b-instruct:free", 2),
]

DEFAULT_MAX_TOKENS = 350
DEFAULT_TEMPERATURE = 0.7
REQUEST_TIMEOUT = 30  # seconds


class AIClientError(Exception):
    """Raised when all models fail."""
    pass


def call_openrouter(system_prompt: str, user_message: str) -> str:
    """
    Send a chat completion request to OpenRouter with retry + fallback.

    Args:
        system_prompt: The system instruction (compact context included)
        user_message: The user's raw message

    Returns:
        The AI's reply text

    Raises:
        AIClientError: If all models and retries are exhausted
    """
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        raise AIClientError("OPENROUTER_API_KEY is not configured in settings.")

    # Log payload size for debugging
    total_prompt_chars = len(system_prompt) + len(user_message)
    logger.info(f"📤 Prompt size: {total_prompt_chars} chars (~{total_prompt_chars // 4} tokens)")

    last_error = None

    for model_name, max_retries in MODEL_PIPELINE:
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🤖 Trying {model_name} (attempt {attempt}/{max_retries})")

                response = http_requests.post(
                    OPENROUTER_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://hostelin.online",
                        "X-Title": "Hostel In AI Assistant",
                    },
                    json={
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message},
                        ],
                        "max_tokens": DEFAULT_MAX_TOKENS,
                        "temperature": DEFAULT_TEMPERATURE,
                    },
                    timeout=REQUEST_TIMEOUT,
                )

                # ── Log raw response status ──────────────────────────────
                logger.info(f"📥 Response status: {response.status_code}")

                # ── Check HTTP-level errors ───────────────────────────────
                if response.status_code == 429:
                    last_error = "Rate limited"
                    logger.warning(f"⚠️ {model_name}: Rate limited. Waiting before retry...")
                    time.sleep(2 * attempt)  # Exponential backoff
                    continue

                if response.status_code >= 500:
                    last_error = f"Server error: {response.status_code}"
                    logger.warning(f"⚠️ {model_name}: Server error {response.status_code}")
                    time.sleep(1)
                    continue

                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"⚠️ {model_name}: {last_error}")
                    continue

                # ── Parse JSON ────────────────────────────────────────────
                data = response.json()

                if "error" in data:
                    last_error = data["error"].get("message", str(data["error"]))
                    logger.warning(f"⚠️ {model_name}: API error — {last_error}")
                    time.sleep(1)
                    continue

                # ── Extract reply ─────────────────────────────────────────
                reply = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )

                if not reply:
                    last_error = "Empty response"
                    logger.warning(f"⚠️ {model_name}: Empty response, retrying...")
                    time.sleep(1)
                    continue

                logger.info(f"✅ Success with {model_name} ({len(reply)} chars)")
                return reply

            except http_requests.exceptions.Timeout:
                last_error = f"Timeout after {REQUEST_TIMEOUT}s"
                logger.warning(f"⚠️ {model_name}: {last_error}")
                continue

            except http_requests.exceptions.ConnectionError as e:
                last_error = f"Connection error: {e}"
                logger.warning(f"⚠️ {model_name}: {last_error}")
                time.sleep(1)
                continue

            except Exception as e:
                last_error = str(e)
                logger.error(f"❌ {model_name}: Unexpected error — {e}")
                continue

    # All models exhausted
    logger.error(f"❌ All AI models failed. Last error: {last_error}")
    raise AIClientError(f"All models failed. Last error: {last_error}")
