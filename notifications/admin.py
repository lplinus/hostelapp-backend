from django.contrib import admin
from .models import Notification, BroadcastNotification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'notification_type', 'created_at')
    search_fields = ('user__email', 'title', 'message')
    readonly_fields = ('created_at',)

@admin.register(BroadcastNotification)
class BroadcastNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'is_processed')
    readonly_fields = ('created_at', 'is_processed')
    search_fields = ('title', 'message')
