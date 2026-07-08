"""
Loads the precomputed FAISS index of verse embeddings (built by
`manage.py precompute_embeddings`, see that command's docstring) and
exposes semantic_candidates() — the top-K semantically closest verse
references to a query, used by matching.py as the first stage of identify.

The index is built over WEB only, not every version: semantic *meaning*
doesn't change between translations, so embedding all 4 versions would
quadruple storage and compute for zero retrieval benefit. Candidates
returned here are (book, chapter, verse) references — matching.py resolves
each one to the actual Verse document(s) in whichever version(s) are
actually being searched, then RapidFuzz reranks against that real text for
the final precision pass.

If the index files don't exist yet (precompute_embeddings has never been
run) or faiss isn't installed, everything here degrades to returning None/
empty rather than raising — matching.py falls back to lexical-only search
in that case.
"""
import json
import logging
import threading
from pathlib import Path

from .embeddings import get_embeddings

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
INDEX_PATH = DATA_DIR / "verse_embeddings.faiss"
META_PATH = DATA_DIR / "verse_embeddings_meta.json"
EMBEDDING_VERSION = "WEB"  # which version's text was embedded to build the index

_lock = threading.Lock()
_index = None  # faiss.Index, or False if unavailable (load attempted and failed)
_meta = None  # list of [book, chapter, verse], same order as index vectors


def _l2_normalize(vec: list[float]):
    import numpy as np

    arr = np.array(vec, dtype="float32")
    norm = np.linalg.norm(arr)
    if norm == 0:
        return arr
    return arr / norm


def _load():
    """Lazily loads the index + metadata once per process, caching the
    result (including a cached "unavailable" state so a missing index
    doesn't retry a disk read on every single search)."""
    global _index, _meta

    if _index is not None:
        return

    with _lock:
        if _index is not None:  # re-check after acquiring the lock
            return

        if not INDEX_PATH.exists() or not META_PATH.exists():
            logger.info(
                "No FAISS index found at %s — semantic search will run "
                "lexical-only until `manage.py precompute_embeddings` is run.",
                INDEX_PATH,
            )
            _index = False
            _meta = False
            return

        try:
            import faiss

            _index = faiss.read_index(str(INDEX_PATH))
            _meta = json.loads(META_PATH.read_text())
        except Exception:
            logger.exception("Failed to load FAISS index — falling back to lexical-only search")
            _index = False
            _meta = False


def semantic_candidates(query: str, k: int = 20) -> list[tuple[str, int, int, float]]:
    """
    Returns up to k (book, chapter, verse, similarity) tuples for the
    query, ranked by cosine similarity — or [] if semantic search isn't
    available right now (no index built, no HF token, API error, etc).
    """
    _load()
    if not _index or not _meta:
        return []

    vectors = get_embeddings([query])
    if not vectors:
        return []

    query_vec = _l2_normalize(vectors[0]).reshape(1, -1)
    similarities, indices = _index.search(query_vec, k)

    results = []
    for idx, sim in zip(indices[0], similarities[0]):
        if idx == -1:
            continue
        book, chapter, verse_num = _meta[idx]
        results.append((book, chapter, verse_num, float(sim)))
    return results


def build_index(book_chapter_verse_vectors) -> None:
    """
    Writes a fresh FAISS index + metadata file to disk. Called by
    `manage.py precompute_embeddings`, not used at query time.

    book_chapter_verse_vectors: iterable of (book, chapter, verse, vector)
    """
    import faiss
    import numpy as np

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    refs = []
    vectors = []
    for book, chapter, verse_num, vector in book_chapter_verse_vectors:
        refs.append([book, chapter, verse_num])
        vectors.append(_l2_normalize(vector))

    matrix = np.vstack(vectors).astype("float32")
    # Inner product on L2-normalized vectors == cosine similarity, and
    # IndexFlatIP is exact (no approximation) — at ~31k vectors this is
    # both fast enough and simpler to reason about than an ANN index.
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)

    faiss.write_index(index, str(INDEX_PATH))
    META_PATH.write_text(json.dumps(refs))

    # Force the next semantic_candidates() call (in this or a future
    # process) to reload from the freshly-written files.
    global _index, _meta
    _index = None
    _meta = None