from django.urls import path

from .views import IdentifyView, RecentSearchesView

urlpatterns = [
    path("identify/", IdentifyView.as_view(), name="search-identify"),
    path("recent/", RecentSearchesView.as_view(), name="search-recent"),
]
