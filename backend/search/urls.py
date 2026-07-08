from django.urls import path

from .views import ClearHistoryView, HistoryItemView, IdentifyView, RecentSearchesView

urlpatterns = [
    path("identify/", IdentifyView.as_view(), name="search-identify"),
    path("recent/", RecentSearchesView.as_view(), name="search-recent"),
    path("history/", ClearHistoryView.as_view(), name="search-history-clear"),
    path("history/<str:history_id>/", HistoryItemView.as_view(), name="search-history-item"),
]
