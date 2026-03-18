"""
URL configuration for Hbackend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import mimetypes
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # DRF Spectacular schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # App URLs
    path("api/auth/", include("accounts.auth_urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/amenities/", include("amenities.urls")),
    path("api/locations/", include("locations.urls")),
    path("api/hostels/", include("hostels.urls")),
    path("api/rooms/", include("rooms.urls")),
    path("api/bookings/", include("bookings.urls")),
    path("api/reviews/", include("reviews.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/seo/", include("seo.urls")),
    path("api/cms/", include("cms.urls")),
    path("api/blog/", include("blog.urls")),
    path("api/publicpages/", include("publicpages.urls")),
    path(
        "api/dashboard/stats/",
        __import__(
            "accounts.views.user_views", fromlist=["DashboardStatsView"]
        ).DashboardStatsView.as_view(),
        name="dashboard_stats",
    ),
    path(
        "api/users/me/",
        __import__(
            "accounts.views.user_views", fromlist=["UserMeView"]
        ).UserMeView.as_view(),
        name="user_me",
    ),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
