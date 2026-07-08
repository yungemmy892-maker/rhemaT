"""
Builds the FAISS index of verse embeddings used by semantic search
(search/faiss_index.py). Run this once after loading Bible data, and again
any time WEB's verse data changes:

    python manage.py precompute_embeddings

Only WEB is embedded (~31k verses) — semantic *meaning* doesn't change
between translations, so embedding KJV/ASV/DRA too would triple storage
and compute for zero retrieval benefit. matching.py resolves each semantic
hit to whichever version(s) are actually being searched afterward.

Takes a while (one HF API call per batch, ~310 calls at BATCH_SIZE=100 for
the full WEB corpus) — this is a rare, offline, one-time operation, not
something that runs per-request, so it isn't optimized for speed.
"""
import sys
import time

from django.core.management.base import BaseCommand, CommandError

from bible.models import Verse
from search.embeddings import get_embeddings
from search.faiss_index import EMBEDDING_VERSION, build_index

BATCH_SIZE = 100
RETRY_DELAY_SECONDS = 5
MAX_RETRIES = 3


class Command(BaseCommand):
    help = "Precompute and store FAISS embeddings for semantic verse search."

    def handle(self, *args, **options):
        verses = list(Verse.objects(version=EMBEDDING_VERSION).order_by("book_index", "chapter", "verse"))
        if not verses:
            raise CommandError(
                f"No {EMBEDDING_VERSION} verses found — run `manage.py load_bible "
                f"--version {EMBEDDING_VERSION.lower()}` first."
            )

        total = len(verses)
        self.stdout.write(f"Embedding {total} {EMBEDDING_VERSION} verses in batches of {BATCH_SIZE}...")

        rows = []  # (book, chapter, verse, vector)
        for start in range(0, total, BATCH_SIZE):
            batch = verses[start : start + BATCH_SIZE]
            texts = [v.text for v in batch]

            vectors = None
            for attempt in range(1, MAX_RETRIES + 1):
                vectors = get_embeddings(texts)
                if vectors is not None:
                    break
                self.stderr.write(
                    self.style.WARNING(
                        f"  batch {start}-{start + len(batch)}: embedding request failed "
                        f"(attempt {attempt}/{MAX_RETRIES}), retrying in {RETRY_DELAY_SECONDS}s..."
                    )
                )
                time.sleep(RETRY_DELAY_SECONDS)

            if vectors is None:
                raise CommandError(
                    f"Failed to embed batch starting at verse {start} after {MAX_RETRIES} attempts. "
                    "Check HF_API_TOKEN is set and valid, and that you have Inference Providers credit "
                    "remaining. Partial progress was NOT saved — just re-run the command once fixed."
                )

            for verse, vector in zip(batch, vectors):
                rows.append((verse.book, verse.chapter, verse.verse, vector))

            done = start + len(batch)
            sys.stdout.write(f"\r  {done}/{total} embedded")
            sys.stdout.flush()

        sys.stdout.write("\n")
        self.stdout.write("Building FAISS index...")
        build_index(rows)
        self.stdout.write(self.style.SUCCESS(f"Done — indexed {len(rows)} verses to search/data/."))