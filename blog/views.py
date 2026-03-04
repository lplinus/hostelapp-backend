from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.permissions import AllowAny
from django.db.models import Prefetch

from .models import Blog, BlogPost, BlogCategory
from .serializers import (
    BlogSerializer,
    BlogPostListSerializer,
    BlogPostDetailSerializer,
    BlogCategorySerializer,
)


class BlogAPIView(RetrieveAPIView):
    serializer_class = BlogSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        return get_object_or_404(
            Blog.objects,
            is_active=True
        )


class BlogPostListAPIView(ListAPIView):
    serializer_class = BlogPostListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return (
            BlogPost.objects
            .select_related("category")
            .filter(is_published=True)
        )


class BlogPostDetailAPIView(RetrieveAPIView):
    serializer_class = BlogPostDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return (
            BlogPost.objects
            .select_related("category")
            .filter(is_published=True)
        )


class BlogCategoryListAPIView(ListAPIView):
    serializer_class = BlogCategorySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return BlogCategory.objects.all()