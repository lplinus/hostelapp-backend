import re
from datetime import timedelta
from django.utils import timezone
from typing import Optional
from .models import ChatCache

def normalize_question(text: str) -> str:
    """
    Normalizes a user question to increase cache hit rates for similar questions.
    """
    if not text:
        return ""
        
    # 1. Lowercase
    text = text.lower()
    
    # 2. Remove punctuation (keeping only alphanumeric and spaces)
    text = re.sub(r'[^\w\s]', '', text)
    
    # 3. Strip and remove extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 4. Replace synonyms
    synonyms = {
        r'\bprice\b': 'cost',
        r'\brent\b': 'cost',
        r'\bamount\b': 'cost',
        r'\bcharges\b': 'cost',
        r'\bfee\b': 'cost',
        r'\bfees\b': 'cost'
    }
    for pattern, replacement in synonyms.items():
        text = re.sub(pattern, replacement, text)
        
    return text[:500]

class ChatCacheService:
    @staticmethod
    def get_cached_answer(question: str) -> Optional[str]:
        """
        Check if an answer for this question is already cached and valid.
        Uses a 48-hour TTL to ensure chatbot data updates gracefully.
        """
        normalized = normalize_question(question)
        if not normalized:
            return None
            
        expiry_time = timezone.now() - timedelta(hours=48)
        
        # Optimize query: index on normalized_question, select only 'answer', limit to first()
        cached = ChatCache.objects.filter(
            normalized_question=normalized,
            updated_at__gte=expiry_time
        ).only('answer').first()
        
        if cached:
            return cached.answer
        return None

    @staticmethod
    def store_answer(question: str, answer: str) -> None:
        """
        Store a generated answer in the cache, or update an existing one for the same normalized question.
        Also passively cleans up fully expired caches to prevent database bloat.
        """
        normalized = normalize_question(question)
        if not normalized or not answer:
            return
            
        # Using update_or_create to keep the cache fresh and avoid duplicates of the same normalized string
        ChatCache.objects.update_or_create(
            normalized_question=normalized,
            defaults={
                'question': question,
                'answer': answer
            }
        )
        
        # Passive garbage collection: delete rows older than 48 hours
        # Prevents the database from infinitely growing with unused questions over months.
        try:
            expiration = timezone.now() - timedelta(hours=48)
            ChatCache.objects.filter(updated_at__lt=expiration).delete()
        except Exception:
            pass
