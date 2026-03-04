from django.contrib import admin

# Register your models here.
from .models import RoomType, Bed

admin.site.register(RoomType)
admin.site.register(Bed)