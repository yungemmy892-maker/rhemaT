from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.urls import include, path


def health(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health, name="health"),
    path("api/v1/auth/", include("auth_api.urls")),
    path("api/v1/bible/", include("bible.urls")),
    path("api/v1/search/", include("search.urls")),
    path("api/v1/preferences/", include("preferences.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/billing/", include("billing.urls")),
]

if settings.DEBUG:
    # In production, serve MEDIA_ROOT with your web server/CDN instead.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
