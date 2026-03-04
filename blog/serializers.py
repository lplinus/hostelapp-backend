from rest_framework import serializers
from .models import Blog, BlogCategory, BlogPost


class BlogCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogCategory
        fields = ["id", "name", "slug"]


class BlogPostListSerializer(serializers.ModelSerializer):
    category = BlogCategorySerializer(read_only=True)
    banner_image = serializers.ImageField(read_only=True)
    featured_image = serializers.ImageField(read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "banner_image",
            "featured_image",
            "read_time",
            "created_at",
            "category",
        ]


class BlogPostDetailSerializer(serializers.ModelSerializer):
    category = BlogCategorySerializer(read_only=True)
    banner_image = serializers.ImageField(read_only=True)
    featured_image = serializers.ImageField(read_only=True)
    featured_image2 = serializers.ImageField(read_only=True)
    featured_image3 = serializers.ImageField(read_only=True)

    class Meta:
        model = BlogPost
        fields = [
            "id",
            "title",
            "slug",
            "short_description",
            "content",
            "banner_image",
            "featured_image",
            "featured_image2",
            "featured_image3",
            "read_time",
            "created_at",
            "updated_at",
            "category",
        ]


class BlogSerializer(serializers.ModelSerializer):
    class Meta:
        model = Blog
        fields = [
            "hero_title",
            "hero_subtitle",
        ]
