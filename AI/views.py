import time
import requests as http_requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import get_hostel_knowledge_base


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Primary model with retries, then fallbacks
MODEL_ATTEMPTS = [
    ("openrouter/free", 5),                                    # Try the auto-router 3 times
    ("meta-llama/llama-3.3-70b-instruct:free", 2),            # Fallback 1
]


class ChatbotView(APIView):
    """
    AI Chatbot powered by OpenRouter free models with real-time hostel context.
    Includes retry logic for reliability.
    """

    def post(self, request):
        user_message = request.data.get("message")
        if not user_message:
            return Response(
                {"error": "Message is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Validate API key
        api_key = settings.OPENROUTER_API_KEY
        if not api_key:
            return Response(
                {"error": "AI API Key not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 2. Build the knowledge base from real DB data
        knowledge_base = get_hostel_knowledge_base()

        system_prompt = f"""You are the official 'Hostel In' AI Assistant — a friendly, knowledgeable hostel concierge.

Here is the COMPLETE database of all our hostels:
{knowledge_base}

RESPONSE FORMAT RULES:
1. Use ONLY the data provided above. Never make up hostel names, prices, or details.
2. If asked about a city or hostel NOT in the data, say: "We're expanding there soon! For now, check our available cities."
3. Keep responses concise (3-5 sentences). Use bullet points for lists.
4. Format prices strictly as ₹X,XXX/month (e.g., ₹6,000/month). NEVER include decimals or .0.
5. When listing hostels, include: Name, City, Type, Starting Price, and key amenities.
6. If the user asks to book, tell them to visit the hostel page and click 'Book Now'.
7. For complaints or support, suggest WhatsApp at 9392356996.
8. Be warm and professional. Use emojis sparingly (1-2 max per response).
9. NEVER use markdown formatting like ** or ##. Use plain text only.
10. Use line breaks to separate different points for readability."""

        # 3. Try models with retry logic
        last_error = None
        for model_name, max_retries in MODEL_ATTEMPTS:
            for attempt in range(max_retries):
                try:
                    print(f"🤖 Trying {model_name} (attempt {attempt + 1}/{max_retries})")
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
                            "max_tokens": 600,
                            "temperature": 0.7,
                        },
                        timeout=30,
                    )

                    data = response.json()

                    # Check for API errors
                    if "error" in data:
                        last_error = data["error"].get("message", str(data["error"]))
                        print(f"⚠️ {model_name} failed: {last_error}")
                        time.sleep(1)  # Brief pause before retry
                        continue

                    # Extract the reply
                    reply_text = (
                        data.get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )

                    if not reply_text:
                        last_error = "Empty response"
                        print(f"⚠️ {model_name}: empty response, retrying...")
                        time.sleep(1)
                        continue

                    print(f"✅ Success with {model_name}")
                    return Response({
                        "reply": reply_text,
                        "status": "success",
                    })

                except Exception as e:
                    last_error = str(e)
                    print(f"⚠️ {model_name} error: {e}")
                    time.sleep(1)
                    continue

        # All attempts failed
        print(f"❌ All AI models failed. Last error: {last_error}")
        return Response(
            {
                "error": "The AI assistant is temporarily unavailable. Please try again in a moment.",
                "details": str(last_error),
                "status": "failed",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
