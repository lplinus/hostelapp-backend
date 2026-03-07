from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
# from django.utils import timezone


class SeoMeta(models.Model):
    # Generic relation (attach to Hostel, City, Page, etc.)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    # Basic SEO
    meta_title = models.CharField(max_length=255)
    meta_description = models.TextField()
    meta_keywords = models.TextField(null=True, blank=True)

    canonical_url = models.URLField(blank=True, null=True)

    # OpenGraph
    og_title = models.CharField(max_length=255, blank=True, null=True)
    og_description = models.TextField(blank=True, null=True)
    og_image = models.URLField(blank=True, null=True)

    # Technical SEO
    is_indexed = models.BooleanField(default=True)
    robots_directives = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Example: noindex, nofollow"
    )

    # Structured Data
    structured_data = models.JSONField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.meta_title