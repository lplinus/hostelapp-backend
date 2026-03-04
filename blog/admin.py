from django.contrib import admin
from .models import Blog, BlogPost, BlogCategory

# Register your models here.
admin.site.register(Blog)
admin.site.register(BlogPost)
admin.site.register(BlogCategory)