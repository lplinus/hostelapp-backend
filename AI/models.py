from django.db import models

class ChatCache(models.Model):
    """
    Caches chatbot answers based on normalized questions to avoid redundant AI API calls.
    """
    question = models.TextField(help_text="Original user question")
    normalized_question = models.CharField(
        max_length=500,
        db_index=True, 
        help_text="Normalized version for matching similar questions"
    )
    answer = models.TextField(help_text="AI generated answer")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Chat Caches"

    def __str__(self):
        return f"Cache for: {self.question[:50]}..."
