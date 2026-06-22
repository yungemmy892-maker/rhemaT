"""
Verse identification engine.

Strategy (kept dependency-light — no external search service):
  1. Use MongoDB's text index to pull a candidate shortlist (fast, scales to
     31k verses without scanning every document on every request).
  2. Re-rank candidates with RapidFuzz token-based fuzzy matching, which
     tolerates misremembered words, paraphrasing, and partial phrases —
     much closer to "Shazam for Bible verses" than a strict substring match.
  3. If the text index returns nothing (e.g. very short or unusual query),
     fall back to a bounded scan so short queries like "be still" still work.

Each match reports which of four named signals drove the result —
phrase match, partial match, token-set match, or fuzzy-typo match — plus
the blended confidence score, so the API response can be explicit about
*why* a verse matched instead of returning an opaque number.
"""

from rapidfuzz import fuzz

from bible.models import Verse

CANDIDATE_LIMIT = 60
FALLBACK_SCAN_LIMIT = 4000
# Tuned empirically against real KJV+WEB text across ~15 known-verse test
# queries plus noise queries (see scripts/check_matching.py). At this
# threshold, well-known verses quoted approximately score 0.73-0.95;
# unrelated/gibberish queries top out around 0.65-0.72. The gap is real but
# narrow — lexical fuzzy matching alone cannot perfectly separate every
# case. Known false negatives: verses whose KJV/WEB wording differs
# substantially from common modern paraphrase (e.g. KJV's "Be careful for
# nothing" for what's commonly recalled as "do not be anxious", or
# Jeremiah 29:11's "thoughts...to give you an expected end" for "I have
# plans to prosper you") can still score below threshold in both versions.
# Closing this fully would need a synonym map or semantic embeddings —
# out of scope for this pass, documented here rather than silently shipped.
MIN_CONFIDENCE = 0.65

def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _strip_punct(text: str) -> str:
    return "".join(ch for ch in text if ch.isalnum() or ch.isspace())


def _match_breakdown(query: str, verse_text_lower: str) -> dict:
    """
    Computes all four named signals plus the blended confidence score.

    - phrase:    near-exact substring containment (query literally appears
                 in the verse, modulo punctuation/whitespace).
    - partial:   RapidFuzz partial_ratio — the query is a fragment of a
                 longer verse (most common case: users only recall a clause).
    - token_set: RapidFuzz token_set_ratio — robust to word reordering and
                 to one side having extra/missing words (e.g. dropped
                 "and"/"the"), which token_sort_ratio is more sensitive to.
    - fuzzy_typo: RapidFuzz WRatio — RapidFuzz's general blended heuristic,
                 which best tolerates misspellings, mis-hearings (voice
                 transcription slips), and minor recall errors overall.
    """
    q_clean = _strip_punct(query)
    v_clean = _strip_punct(verse_text_lower)

    phrase_hit = q_clean in v_clean
    phrase_score = 100.0 if phrase_hit else fuzz.partial_ratio(q_clean, v_clean)

    partial_score = fuzz.partial_ratio(query, verse_text_lower)
    token_set_score = fuzz.token_set_ratio(query, verse_text_lower)
    fuzzy_typo_score = fuzz.WRatio(query, verse_text_lower)

    confidence = (
        0.30 * phrase_score + 0.25 * partial_score + 0.15 * token_set_score + 0.30 * fuzzy_typo_score
    ) / 100.0

    return {
        "phraseMatch": round(phrase_score / 100.0, 4),
        "partialMatch": round(partial_score / 100.0, 4),
        "tokenSetMatch": round(token_set_score / 100.0, 4),
        "fuzzyTypoMatch": round(fuzzy_typo_score / 100.0, 4),
        "confidence": round(confidence, 4),
        "exactPhrase": phrase_hit,
    }


def find_best_match(raw_query: str, version: str | None = None):
    """
    Returns {"verse": Verse.to_dict(), **match_breakdown} or None.

    If `version` is given ("KJV" or "WEB"), only that version's text is
    searched. If omitted, both versions are searched and the
    higher-confidence match wins — this is what lets a modern paraphrase
    ("love is patient") succeed via WEB even when it would score too low
    against KJV's "charity" wording alone.
    """
    query = _normalize(raw_query)
    if not query:
        return None

    base_qs = Verse.objects(version=version) if version else Verse.objects

    candidates = list(base_qs.search_text(query).limit(CANDIDATE_LIMIT))
    if not candidates:
        # Text index found nothing (common for very short/common-word
        # queries) — fall back to a bounded scan over a slice of the corpus
        # so the demo never feels broken on short input.
        candidates = list(base_qs[:FALLBACK_SCAN_LIMIT])

    best = None
    best_breakdown = None
    for verse in candidates:
        breakdown = _match_breakdown(query, verse.text_lower)
        if best_breakdown is None or breakdown["confidence"] > best_breakdown["confidence"]:
            best = verse
            best_breakdown = breakdown

    if best is None or best_breakdown["confidence"] < MIN_CONFIDENCE:
        return None

    return {"verse": best.to_dict(), **best_breakdown}


def search_verses(raw_query: str, limit: int = 10, version: str | None = None):
    """Multi-result search used by the text-search suggestions / discover
    flows, returning a ranked list instead of a single best guess."""
    query = _normalize(raw_query)
    if not query:
        return []

    base_qs = Verse.objects(version=version) if version else Verse.objects
    candidates = list(base_qs.search_text(query).limit(CANDIDATE_LIMIT))
    scored = [(v, _match_breakdown(query, v.text_lower)) for v in candidates]
    scored.sort(key=lambda pair: pair[1]["confidence"], reverse=True)
    return [
        {"verse": v.to_dict(), **breakdown}
        for v, breakdown in scored[:limit]
        if breakdown["confidence"] >= MIN_CONFIDENCE
    ]
