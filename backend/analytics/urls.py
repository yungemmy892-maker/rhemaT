from django.urls import path

from .views import AdminStatsView, AdminUserDeleteView, AdminUserSearchView

urlpatterns = [
    path("stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("users/search/", AdminUserSearchView.as_view(), name="admin-user-search"),
    path(
        "users/<str:user_id>/", AdminUserDeleteView.as_view(), name="admin-user-delete"
    ),
]
