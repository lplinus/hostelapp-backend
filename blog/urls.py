from django.urls import path
from .views import (
    BlogAPIView,
    BlogPostListAPIView,
    BlogPostDetailAPIView,
    BlogCategoryListAPIView,
)

urlpatterns = [
    path("blog/", BlogAPIView.as_view(), name="blog-page"),
    path("blog/posts/", BlogPostListAPIView.as_view(), name="blog-post-list"),
    path("blog/posts/<slug:slug>/", BlogPostDetailAPIView.as_view(), name="blog-post-detail"),
    path("blog/categories/", BlogCategoryListAPIView.as_view(), name="blog-categories"),
]