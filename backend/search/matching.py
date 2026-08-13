from rapidfuzz import fuzz

from bible.models import SUPPORTED_VERSIONS, Verse

from .faiss_index import semantic_candidates

# Tuned empirically against real KJV+WEB text across ~15 known-verse test
# queries plus noise queries (see scripts/check_matching.py). At this
# threshold, well-known verses quoted approximately score 0.73-0.95;
# unrelated/gibberish queries top out around 0.65-0.72.
MIN_CONFIDENCE = 0.65

SEMANTIC_TOP_K = 20


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
        0.30 * phrase_score
        + 0.25 * partial_score
        + 0.15 * token_set_score
        + 0.30 * fuzzy_typo_score
    ) / 100.0

    return {
        "phraseMatch": round(phrase_score / 100.0, 4),
        "partialMatch": round(partial_score / 100.0, 4),
        "tokenSetMatch": round(token_set_score / 100.0, 4),
        "fuzzyTypoMatch": round(fuzzy_typo_score / 100.0, 4),
        "confidence": round(confidence, 4),
        "exactPhrase": phrase_hit,
    }


def _version_pool(version: str | None, allowed_versions) -> list[str]:
    """
    KJV/WEB/ASV by default; DRA only when explicitly selected. DRA
    (Douay-Rheims) follows Vulgate-based verse numbering and noticeably
    different wording, which was winning fuzzy-match ties it shouldn't
    against completely unrelated queries when mixed in by default. It still
    matches correctly when a user has it explicitly selected as their
    Bible version.

    `allowed_versions` further restricts the pool to what the requesting
    user's plan can access (see users.models.User.allowed_versions) — a
    Free or Pro user's omitted-version search never pulls in versions
    their plan doesn't include, and a specific `version` is trusted here
    (the caller — search/views.py — is responsible for rejecting a
    request for a version outside the user's plan before ever reaching
    this function).
    """
    if version:
        return [version]
    return [v for v in ("KJV", "WEB", "ASV") if v in allowed_versions]


def _resolve_semantic_hits(hits, version: str | None, allowed_versions) -> list[Verse]:
    """Resolves FAISS's (book, chapter, verse, similarity) references to
    actual Verse documents in every version currently being searched — a
    verse embedded once (WEB) can still surface a KJV or ASV match, since
    identity is by reference, not by which translation was embedded."""
    pool = _version_pool(version, allowed_versions)
    resolved = []
    for book, chapter, verse_num, _similarity in hits:
        resolved.extend(
            Verse.objects(book=book, chapter=chapter, verse=verse_num, version__in=pool)
        )
    return resolved


def _lexical_scan(query: str, version: str | None, allowed_versions) -> list[tuple[Verse, dict]]:
    pool = _version_pool(version, allowed_versions)
    scored = [
        (v, _match_breakdown(query, v.text_lower))
        for v in Verse.objects(version__in=pool)
    ]
    scored.sort(key=lambda pair: pair[1]["confidence"], reverse=True)
    return scored


def find_best_match(raw_query: str, version: str | None = None, allowed_versions=SUPPORTED_VERSIONS):
    """Returns {"verse": Verse.to_dict(), **match_breakdown} or None.

    `allowed_versions` should be the caller's user.allowed_versions() —
    defaults to every SUPPORTED_VERSIONS so existing callers that don't
    pass it (scripts/check_matching.py) keep their current unrestricted
    behavior."""
    query = _normalize(raw_query)
    if not query:
        return None

    hits = semantic_candidates(query, k=SEMANTIC_TOP_K)

    if hits:
        candidates = _resolve_semantic_hits(hits, version, allowed_versions)
        if candidates:
            scored = sorted(
                ((v, _match_breakdown(query, v.text_lower)) for v in candidates),
                key=lambda pair: pair[1]["confidence"],
                reverse=True,
            )
            best, best_breakdown = scored[0]
            if best_breakdown["confidence"] >= MIN_CONFIDENCE:
                return {
                    "verse": best.to_dict(),
                    **best_breakdown,
                    "semanticMatch": True,
                }
            # Semantic search ran successfully and found nothing that
            # actually reads like the query — a real no-match, not a
            # reason to fall back to a full lexical scan.
            return None

    # Semantic search unavailable (no FAISS index yet, no HF token, or the
    # API call failed) — fall back to scoring every verse directly so
    # identify still works at all.
    scored = _lexical_scan(query, version, allowed_versions)
    if not scored or scored[0][1]["confidence"] < MIN_CONFIDENCE:
        return None
    best, best_breakdown = scored[0]
    return {"verse": best.to_dict(), **best_breakdown, "semanticMatch": False}


def search_verses(raw_query: str, limit: int = 10, version: str | None = None, allowed_versions=SUPPORTED_VERSIONS):
    """Multi-result search used by the text-search suggestions / discover
    flows, returning a ranked list instead of a single best guess."""
    query = _normalize(raw_query)
    if not query:
        return []

    hits = semantic_candidates(query, k=SEMANTIC_TOP_K)
    if hits:
        candidates = _resolve_semantic_hits(hits, version, allowed_versions)
        if candidates:
            scored = sorted(
                ((v, _match_breakdown(query, v.text_lower)) for v in candidates),
                key=lambda pair: pair[1]["confidence"],
                reverse=True,
            )
            return [
                {"verse": v.to_dict(), **breakdown}
                for v, breakdown in scored[:limit]
                if breakdown["confidence"] >= MIN_CONFIDENCE
            ]

    scored = _lexical_scan(query, version, allowed_versions)
    return [
        {"verse": v.to_dict(), **breakdown}
        for v, breakdown in scored[:limit]
        if breakdown["confidence"] >= MIN_CONFIDENCE
    ]