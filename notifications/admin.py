from django.contrib import admin
from .models import Notification, BroadcastNotification, FCMDevice, SupportThread, SupportMessage

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

@admin.register(FCMDevice)
class FCMDeviceAdmin(admin.ModelAdmin):
    list_display = ('user', 'vendor', 'device_type', 'is_active', 'created_at', 'updated_at')
    list_filter = ('device_type', 'is_active', 'created_at')
    search_fields = ('user__email', 'vendor__business_name', 'registration_token')
    readonly_fields = ('created_at', 'updated_at')


# ==============================================================================
# 1-ON-1 HELP & SUPPORT CHAT ADMIN
# ==============================================================================

class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 1
    fields = ('sender', 'is_staff_reply', 'body', 'is_read', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(SupportThread)
class SupportThreadAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'subject', 'status', 'last_message_at', 'created_at')
    list_filter = ('subject', 'status', 'created_at')
    search_fields = ('user__email', 'user__username')
    inlines = [SupportMessageInline]


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('thread', 'sender', 'is_staff_reply', 'is_read', 'created_at')
    list_filter = ('is_staff_reply', 'is_read', 'created_at')
    search_fields = ('body', 'sender__email')
