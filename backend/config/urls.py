from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, JsonResponse
from django.urls import include, path
from django.views.generic import TemplateView


def health(request):
    return JsonResponse({"status": "ok"})


def robots_txt(request):
    # This host is 100% API endpoints plus the internal admin dashboard —
    # there is no page content here that should ever appear in search
    # results. (The actual public site's robots.txt lives on the frontend,
    # frontend/public/robots.txt, and allows the real public pages.)
    return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")


urlpatterns = [
    path("health/", health, name="health"),
    path("robots.txt", robots_txt, name="robots-txt"),
    path("api/v1/auth/", include("auth_api.urls")),
    path("api/v1/bible/", include("bible.urls")),
    path("api/v1/search/", include("search.urls")),
    path("api/v1/preferences/", include("preferences.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/billing/", include("billing.urls")),
    path("api/v1/admin/", include("analytics.urls")),
    # Standalone admin analytics dashboard (plain HTML/JS, no build step).
    # Served same-origin from Django specifically so its fetch() calls to
    # /api/v1/admin/stats/ never hit CORS — see analytics/templates/admin_dashboard.html.
    path(
        "admin-dashboard/",
        TemplateView.as_view(template_name="admin_dashboard.html"),
        name="admin-dashboard",
    ),
]

if settings.DEBUG:
    # In production, serve MEDIA_ROOT with your web server/CDN instead.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
