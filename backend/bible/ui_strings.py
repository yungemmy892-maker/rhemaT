"""
Canonical English source strings for VerseID's UI translation feature.

The interface-language setting (Settings → Interface language) translates
*chrome* — navigation, headings, buttons — not Bible text itself, which
stays in its own selected version (KJV/WEB/ASV/DRA) regardless of interface
language; those are two independent settings.

This list intentionally starts with the highest-visibility strings (bottom
nav + Home screen) rather than attempting full coverage of every screen in
one pass — extending it is just adding another "key": "English sentence"
entry here; the frontend's t() helper picks up new keys automatically the
next time a language's cache is (re)warmed.
"""

UI_STRINGS = {
    # Bottom navigation
    "nav.home": "Home",
    "nav.library": "Library",
    "nav.discover": "Discover",
    "nav.profile": "Profile",
    # Home screen
    "home.greeting.morning": "Good morning",
    "home.greeting.afternoon": "Good afternoon",
    "home.greeting.evening": "Good evening",
    "home.tapToIdentify": "Tap to identify a verse",
    "home.recentSearches": "Recent searches",
    "home.verseOfDay": "Verse of the day",
    # Common actions
    "action.save": "Save",
    "action.saved": "Saved",
    "action.share": "Share",
    "action.copy": "Copy",
    "action.tryAgain": "Try again",
    "action.cancel": "Cancel",
    "action.confirm": "Confirm",
    "action.done": "Done",
    "action.back": "Back",
}
