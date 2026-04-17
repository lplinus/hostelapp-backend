from django.contrib import admin
from .models import ChatCache

@admin.register(ChatCache)
class ChatCacheAdmin(admin.ModelAdmin):
    list_display = ('normalized_question', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('question', 'normalized_question')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
