from django.urls import path

from .views import CollectionsView, SavedVersesView, SettingsView

urlpatterns = [
    path("saved/", SavedVersesView.as_view(), name="prefs-saved"),
    path("collections/", CollectionsView.as_view(), name="prefs-collections"),
    path("settings/", SettingsView.as_view(), name="prefs-settings"),
]
