#!/usr/bin/env python
"""
Quick sanity check for the verse-matching engine, meant to be run AFTER
`python manage.py load_bible` against a live MongoDB instance.

Usage (from backend/ with venv active):
    python scripts/check_matching.py

This was validated offline against the raw KJV+WEB fixtures (bypassing
Mongo's $text index) during development — see the git history /
conversation log for the full grid-search used to pick the score weights
in search/matching.py. Mongo's $text search applies English
stemming/stopword removal, which can behave slightly differently from the
offline check — re-run this after loading data to confirm real-world
behavior, especially if you tune MIN_CONFIDENCE.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from search.matching import find_best_match  # noqa: E402

GOOD_QUERIES = [
    ("for god so loved the world", "John 3:16"),
    ("the lord is my shepherd", "Psalms 23:1"),
    ("i can do all things through him who strengthens me", "Philippians 4:13"),
    ("be still and know that i am god", "Psalms 46:10"),
    ("trust in the lord with all your heart", "Proverbs 3:5"),
    ("love is patient love is kind", "1 Corinthians 13:4"),  # only matches via WEB
]

# Known limitations documented in matching.py — these are expected to
# sometimes miss because the KJV/WEB wording differs substantially from
# the modern paraphrase being tested. Listed here so a failure isn't
# mistaken for a regression.
KNOWN_HARD_QUERIES = [
    ("come to me all who are weary", "Matthew 11:28"),
    ("for i know the plans i have for you", "Jeremiah 29:11"),
    ("do not be anxious about anything", "Philippians 4:6"),
]

NOISE_QUERIES = [
    "asdkjfh qwoeiru",
    "pizza delivery tracking number",
    "what time is the meeting tomorrow",
]


def _ref(result):
    v = result["verse"]
    return f"{v['book']} {v['chapter']}:{v['verse']} ({v['version']})"


def run_set(label, queries, expect_match=True):
    print(f"=== {label} ===")
    for query, expected_ref in queries:
        result = find_best_match(query)
        if result is None:
            mark = "✗" if expect_match else "?"
            print(f"  {mark} {query!r} -> NO MATCH (expected {expected_ref})")
            continue
        plain_ref = result["verse"]["book"] + " " + str(result["verse"]["chapter"]) + ":" + str(result["verse"]["verse"])
        mark = "✓" if plain_ref == expected_ref else "✗"
        print(
            f"  {mark} {query!r} -> {_ref(result)} "
            f"[phrase={result['phraseMatch']} partial={result['partialMatch']} "
            f"tokenSet={result['tokenSetMatch']} fuzzyTypo={result['fuzzyTypoMatch']} "
            f"confidence={result['confidence']}] expected {expected_ref}"
        )


def main():
    run_set("Expected matches", GOOD_QUERIES)
    print()
    run_set("Known hard cases (misses here are expected, not bugs)", KNOWN_HARD_QUERIES)

    print("\n=== Noise queries (should mostly return NO MATCH) ===")
    for query in NOISE_QUERIES:
        result = find_best_match(query)
        if result is None:
            print(f"  ✓ {query!r} -> NO MATCH (correct)")
        else:
            print(f"  ✗ {query!r} -> {_ref(result)} (confidence={result['confidence']}) — false positive")


if __name__ == "__main__":
    main()
