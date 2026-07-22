import datetime

from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .languages import LANGUAGES
from .models import SUPPORTED_VERSIONS, Verse
from .translate_service import get_ui_translations

# Bible text (every version currently loaded) is static once
# `manage.py load_bible` has run — nothing in this file ever writes to it —
# so the cache keys below never need explicit invalidation; a TTL alone is
# enough, and it's set generously (a day) since a cache miss just costs one
# MongoDB round trip, not incorrect data. LanguagesView and
# UITranslationsView aren't cached here: LANGUAGES is already an in-memory
# constant (no DB hit to save), and UITranslationsView has its own
# Mongo-backed per-language cache in translate_service.py already.

POPULAR_REFS = [
    ("John", 3, 16),
    ("Psalms", 23, 1),
    ("Philippians", 4, 13),
    ("Romans", 8, 28),
    ("Proverbs", 3, 5),
    ("Isaiah", 40, 31),
    ("Jeremiah", 29, 11),
    ("Matthew", 11, 28),
    ("Psalms", 46, 10),
    ("1Corinthians", 13, 4),
]


def _resolve_version(request) -> str:
    version = request.query_params.get("version", "KJV").upper()
    return version if version in SUPPORTED_VERSIONS else "KJV"


def _lookup(book, chapter, verse, version="KJV"):
    return Verse.objects(
        book=book, chapter=chapter, verse=verse, version=version
    ).first()


class VerseOfDayView(APIView):
    """
    GET /api/v1/bible/verse-of-day/?version=KJV|WEB
    Deterministic per-calendar-day pick from the curated popular list,
    matching the existing `BIBLE_VERSES[date.getDate() % length]` behavior.
    """

    permission_classes = [AllowAny]
    CACHE_TTL = (
        60 * 60 * 25
    )  # a bit over a day; the date in the key is what actually rolls it over

    def get(self, request):
        version = _resolve_version(request)
        today = datetime.date.today()
        cache_key = f"bible:verse-of-day:{today.isoformat()}:{version}"

        data = cache.get(cache_key)
        if data is None:
            day_index = today.day % len(POPULAR_REFS)
            book, chapter, verse_num = POPULAR_REFS[day_index]
            verse = _lookup(book, chapter, verse_num, version)
            if verse is None:
                return Response({"detail": "Verse of the day unavailable."}, status=503)
            data = verse.to_dict()
            cache.set(cache_key, data, self.CACHE_TTL)

        return Response(data)


class PopularVersesView(APIView):
    """GET /api/v1/bible/popular/?version=KJV|WEB — top 5 for Discover."""

    permission_classes = [AllowAny]
    CACHE_TTL = 60 * 60 * 24

    def get(self, request):
        version = _resolve_version(request)
        cache_key = f"bible:popular:{version}"

        results = cache.get(cache_key)
        if results is None:
            results = []
            for book, chapter, verse_num in POPULAR_REFS[:5]:
                verse = _lookup(book, chapter, verse_num, version)
                if verse:
                    results.append(verse.to_dict())
            cache.set(cache_key, results, self.CACHE_TTL)

        return Response(results)


class VerseDetailView(APIView):
    """GET /api/v1/bible/verse/?book=John&chapter=3&verse=16&version=KJV"""

    permission_classes = [AllowAny]
    CACHE_TTL = 60 * 60 * 24

    def get(self, request):
        version = _resolve_version(request)
        book = request.query_params.get("book")
        chapter = request.query_params.get("chapter")
        verse_num = request.query_params.get("verse")
        if not (book and chapter and verse_num):
            return Response(
                {"detail": "book, chapter and verse are required."}, status=400
            )
        try:
            chapter_i, verse_i = int(chapter), int(verse_num)
        except ValueError:
            return Response(
                {"detail": "chapter and verse must be integers."}, status=400
            )

        cache_key = f"bible:verse:{book}:{chapter_i}:{verse_i}:{version}"
        data = cache.get(cache_key)
        if data is None:
            verse = _lookup(book, chapter_i, verse_i, version)
            if verse is None:
                return Response({"detail": "Verse not found."}, status=404)
            data = verse.to_dict()
            cache.set(cache_key, data, self.CACHE_TTL)

        return Response(data)


class ChapterView(APIView):
    """
    GET /api/v1/bible/chapter/?book=John&chapter=3&version=KJV
    Returns all verses in the chapter — used by the "Read full chapter"
    expandable panel on the Results screen.
    """

    permission_classes = [AllowAny]
    CACHE_TTL = 60 * 60 * 24

    def get(self, request):
        version = _resolve_version(request)
        book = request.query_params.get("book")
        chapter = request.query_params.get("chapter")
        if not (book and chapter):
            return Response({"detail": "book and chapter are required."}, status=400)
        try:
            chapter_num = int(chapter)
        except ValueError:
            return Response({"detail": "chapter must be an integer."}, status=400)

        cache_key = f"bible:chapter:{book}:{chapter_num}:{version}"
        data = cache.get(cache_key)
        if data is None:
            verses = Verse.objects(
                book=book, chapter=chapter_num, version=version
            ).order_by("verse")
            if not verses:
                return Response({"detail": "Chapter not found."}, status=404)
            data = [v.to_dict() for v in verses]
            cache.set(cache_key, data, self.CACHE_TTL)

        return Response(data)


class BooksListView(APIView):
    """GET /api/v1/bible/books/ — canonical 66-book list with testament,
    used if the frontend ever needs a book picker beyond the current mock."""

    permission_classes = [AllowAny]
    CACHE_KEY = "bible:books"
    CACHE_TTL = 60 * 60 * 24

    def get(self, request):
        books = cache.get(self.CACHE_KEY)
        if books is None:
            # distinct() doesn't preserve canonical order, so resolve via
            # one representative document per book to recover
            # book_index/testament — 66 extra round trips, which is exactly
            # why this endpoint is worth caching.
            pipeline_books = Verse.objects.distinct("book")
            books = []
            for book in pipeline_books:
                v = (
                    Verse.objects(book=book)
                    .only("book", "book_display", "testament", "book_index")
                    .first()
                )
                if v:
                    books.append(
                        {
                            "book": v.book,
                            "display": v.book_display,
                            "testament": v.testament,
                            "order": v.book_index,
                        }
                    )
            books.sort(key=lambda b: b["order"])
            cache.set(self.CACHE_KEY, books, self.CACHE_TTL)

        return Response(books)


class LanguagesView(APIView):
    """GET /api/v1/bible/languages/ — all supported UI languages."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(LANGUAGES)


class UITranslationsView(APIView):
    """
    GET /api/v1/bible/translations/?lang=yo — translated UI chrome strings
    for the given interface-language code. Returns {} for English (nothing
    to override) or for a language Google Translate doesn't recognise. Cached in
    Mongo after the first request per language — see translate_service.py.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        lang_code = (request.query_params.get("lang") or "en").strip()
        return Response(get_ui_translations(lang_code))
