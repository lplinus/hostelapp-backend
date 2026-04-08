from django.contrib import admin
from Hbackend.base_models import SoftDeleteAdmin
from .models import Blog, BlogPost, BlogCategory

@admin.register(Blog)
class BlogAdmin(SoftDeleteAdmin):
    list_display = ("hero_title", "is_active", "is_deleted", "created_at")
    list_filter = ("is_active", "is_deleted")
    search_fields = ("hero_title", "hero_subtitle")

@admin.register(BlogCategory)
class BlogCategoryAdmin(SoftDeleteAdmin):
    list_display = ("name", "slug", "is_deleted")
    list_filter = ("is_deleted",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(BlogPost)
class BlogPostAdmin(SoftDeleteAdmin):
    list_display = ("title", "category", "read_time", "is_published", "is_deleted", "created_at")
    list_filter = ("category", "is_published", "is_deleted")
    search_fields = ("title", "short_description", "content")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Basic Information", {
            "fields": ("title", "slug", "category", "read_time", "is_published", "is_deleted")
        }),
        ("Content", {
            "fields": ("short_description", "content", "banner_image", "featured_image", "featured_image2", "featured_image3")
        }),
        ("SEO Settings", {
            "fields": ("meta_title", "meta_description", "meta_keywords", "canonical_url", "is_indexed", "og_title", "og_description", "og_image", "og_type", "structured_data")
        }),
    )