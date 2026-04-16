"""
AI Views — Thin controller layer.

No business logic here. Only orchestrates: Request → Service → Response.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import AIChatService


class ChatbotView(APIView):
    """
    POST /api/ai/chat/
    Body: {"message": "string"}

    Thin controller — delegates all logic to AIChatService.
    """

    def post(self, request):
        user_message = request.data.get("message", "").strip()

        if not user_message:
            return Response(
                {"error": "Message is required", "status": "failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = AIChatService.get_response(user_message)

        if result["status"] == "success":
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
