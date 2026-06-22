import mongoengine as me

SUPPORTED_VERSIONS = ("KJV", "WEB")


class Verse(me.Document):
    """
    A single Bible verse in one of the two supported public-domain
    versions: KJV (King James Version) and WEB (World English Bible).
    Loaded via `manage.py load_bible --version kjv|web`.

    `id` (the public-facing identifier returned to the frontend, e.g.
    "john-3-16") is intentionally version-independent: saving/history
    reference a verse by its book/chapter/verse location, not by which
    translation it was matched in, so a save made from a KJV search and
    one from a WEB search of the same verse are treated as the same
    saved item.
    """

    book = me.StringField(required=True)             # canonical key, e.g. "1Corinthians"
    book_display = me.StringField(required=True)      # "1 Corinthians"
    testament = me.StringField(choices=("OT", "NT"), required=True)
    book_index = me.IntField(required=True)            # 0-based canonical order
    chapter = me.IntField(required=True)
    verse = me.IntField(required=True)
    text = me.StringField(required=True)
    ref = me.StringField(required=True)                # "1 Corinthians 13:4"
    version = me.StringField(choices=SUPPORTED_VERSIONS, required=True)

    # Precomputed lowercase text for fast substring/phrase search, so the
    # search app doesn't lowercase 31k rows on every request.
    text_lower = me.StringField(required=True)

    meta = {
        "collection": "bible_verses",
        "indexes": [
            "book",
            "version",
            ("book_index", "chapter", "verse", "version"),
            {"fields": ["$text_lower", "$ref"], "default_language": "english"},
        ],
    }

    def to_dict(self):
        return {
            "id": f"{self.book.lower()}-{self.chapter}-{self.verse}",
            "book": self.book_display,
            "chapter": self.chapter,
            "verse": self.verse,
            "text": self.text,
            "version": self.version,
            "ref": self.ref,
            "testament": self.testament,
        }


def resolve_verse(verse_id: str, version: str = "KJV"):
    """
    Resolves a public verse id like "john-3-16" (book.lower()-chapter-verse)
    back to a Verse document in the requested version. Falls back to KJV if
    the requested version doesn't have that verse (e.g. WEB's handful of
    Acts verses absent due to differing manuscript basis).
    """
    try:
        book_key, chapter_str, verse_str = verse_id.rsplit("-", 2)
        chapter, verse_num = int(chapter_str), int(verse_str)
    except ValueError:
        return None

    doc = Verse.objects(
        book__iexact=book_key, chapter=chapter, verse=verse_num, version=version
    ).first()
    if doc is None and version != "KJV":
        doc = Verse.objects(
            book__iexact=book_key, chapter=chapter, verse=verse_num, version="KJV"
        ).first()
    return doc
