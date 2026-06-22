import datetime

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SUPPORTED_VERSIONS, Verse

# Well-known references used to seed "Popular verses" on Discover, since
# the corpus itself carries no popularity metadata. Same well-loved verses
# the static mock previously hardcoded, now resolved against real KJV/WEB
# text in MongoDB instead of a 10-item JS array.
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
    return Verse.objects(book=book, chapter=chapter, verse=verse, version=version).first()


class VerseOfDayView(APIView):
    """
    GET /api/v1/bible/verse-of-day/?version=KJV|WEB
    Deterministic per-calendar-day pick from the curated popular list,
    matching the existing `BIBLE_VERSES[date.getDate() % length]` behavior.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        version = _resolve_version(request)
        day_index = datetime.date.today().day % len(POPULAR_REFS)
        book, chapter, verse_num = POPULAR_REFS[day_index]
        verse = _lookup(book, chapter, verse_num, version)
        if verse is None:
            return Response({"detail": "Verse of the day unavailable."}, status=503)
        return Response(verse.to_dict())


class PopularVersesView(APIView):
    """GET /api/v1/bible/popular/?version=KJV|WEB — top 5 for Discover."""

    permission_classes = [AllowAny]

    def get(self, request):
        version = _resolve_version(request)
        results = []
        for book, chapter, verse_num in POPULAR_REFS[:5]:
            verse = _lookup(book, chapter, verse_num, version)
            if verse:
                results.append(verse.to_dict())
        return Response(results)


class VerseDetailView(APIView):
    """GET /api/v1/bible/verse/?book=John&chapter=3&verse=16&version=KJV"""

    permission_classes = [AllowAny]

    def get(self, request):
        version = _resolve_version(request)
        book = request.query_params.get("book")
        chapter = request.query_params.get("chapter")
        verse_num = request.query_params.get("verse")
        if not (book and chapter and verse_num):
            return Response({"detail": "book, chapter and verse are required."}, status=400)
        try:
            verse = _lookup(book, int(chapter), int(verse_num), version)
        except ValueError:
            return Response({"detail": "chapter and verse must be integers."}, status=400)
        if verse is None:
            return Response({"detail": "Verse not found."}, status=404)
        return Response(verse.to_dict())


class ChapterView(APIView):
    """
    GET /api/v1/bible/chapter/?book=John&chapter=3&version=KJV
    Returns all verses in the chapter — used by the "Read full chapter"
    expandable panel on the Results screen.
    """

    permission_classes = [AllowAny]

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

        verses = Verse.objects(book=book, chapter=chapter_num, version=version).order_by("verse")
        if not verses:
            return Response({"detail": "Chapter not found."}, status=404)
        return Response([v.to_dict() for v in verses])


class BooksListView(APIView):
    """GET /api/v1/bible/books/ — canonical 66-book list with testament,
    used if the frontend ever needs a book picker beyond the current mock."""

    permission_classes = [AllowAny]

    def get(self, request):
        pipeline_books = Verse.objects.distinct("book")
        # distinct() doesn't preserve canonical order, so resolve via one
        # representative document per book to recover book_index/testament.
        books = []
        for book in pipeline_books:
            v = Verse.objects(book=book).only("book", "book_display", "testament", "book_index").first()
            if v:
                books.append({
                    "book": v.book,
                    "display": v.book_display,
                    "testament": v.testament,
                    "order": v.book_index,
                })
        books.sort(key=lambda b: b["order"])
        return Response(books)
