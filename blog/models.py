from django.db import models
from Hbackend.utils import process_image_fields


# Create your models here.
class Blog(models.Model):
    hero_title = models.CharField(max_length=255)
    hero_subtitle = models.TextField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "public_blog"
        verbose_name = "Blog Page"
        verbose_name_plural = "Blog Page"

    def __str__(self) -> str:
        return "Blog Page"


class BlogCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        db_table = "public_blog_categories"

    def __str__(self) -> str:
        return self.name


class BlogPost(models.Model):
    category = models.ForeignKey(
        BlogCategory, on_delete=models.CASCADE, related_name="posts"
    )

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)

    short_description = models.TextField()
    content = models.TextField()  # Full blog content (HTML or markdown)

    banner_image = models.ImageField(null=True, blank=True, upload_to="blog/")
    featured_image = models.ImageField(upload_to="blog/")
    featured_image2 = models.ImageField(null=True, blank=True, upload_to="blog/")
    featured_image3 = models.ImageField(null=True, blank=True, upload_to="blog/")
    read_time = models.CharField(max_length=50)  # "5 min"

    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "public_blog_posts"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Convert all image fields to WebP on save
        process_image_fields(
            self,
            ["banner_image", "featured_image", "featured_image2", "featured_image3"],
        )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title
