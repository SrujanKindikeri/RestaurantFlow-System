# =============================================================================
# RestaurantFlow — Root URL Configuration
# =============================================================================

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # API v1
    path("api/", include("core.urls")),
    path("api/", include("accounts.urls")),
    path("api/", include("organizations.urls")),
    path("api/", include("counters.urls")),
    path("api/", include("menu.urls")),
    path("api/", include("orders.urls")),
    path("api/", include("kitchen.urls")),
    path("api/", include("billing.urls")),
    path("api/", include("payments.urls")),
    path("api/", include("inventory.urls")),
    path("api/", include("recipes.urls")),
    path("api/", include("financials.urls")),
    path("api/", include("accounting.urls")),
    path("api/", include("reporting.urls")),
    path("api/", include("central_control.urls")),
    # Phase 16 — Notification & Communication Center
    path("api/", include("notifications.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
