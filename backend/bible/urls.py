from django.urls import path

from .views import BooksListView, ChapterView, LanguagesView, PopularVersesView, VerseDetailView, VerseOfDayView

urlpatterns = [
    path("verse-of-day/", VerseOfDayView.as_view(), name="bible-verse-of-day"),
    path("popular/", PopularVersesView.as_view(), name="bible-popular"),
    path("verse/", VerseDetailView.as_view(), name="bible-verse-detail"),
    path("chapter/", ChapterView.as_view(), name="bible-chapter"),
    path("books/", BooksListView.as_view(), name="bible-books"),
    path("languages/", LanguagesView.as_view(), name="bible-languages"),
]
