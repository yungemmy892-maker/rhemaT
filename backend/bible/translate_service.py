"""
Translates VerseID's UI chrome strings into the user's chosen interface
language, via the free MyMemory Translation API (no API key required —
https://mymemory.translated.net/doc/spec.php). Every (language, key) pair
is translated at most once ever; after that it's served from the
UITranslation cache in Mongo, since MyMemory's anonymous tier has a modest
daily word quota shared across all VerseID users.

MyMemory expects ISO 639-1-ish language codes, which is what
bible/languages.py already stores in LANGUAGES[i]["code"] — but MyMemory
doesn't recognise every code in that list (some of the smaller Nigerian/
West African languages aren't in its language database). When a translation
request fails or the language isn't supported, we fall back to the English
source string for that key rather than surfacing an error — a partially-
translated screen (or an all-English one) is a much better experience than
a broken Settings page.
"""
import logging

import requests

from .models import UITranslation
from .ui_strings import UI_STRINGS

logger = logging.getLogger(__name__)

MYMEMORY_URL = "https://api.mymemory.translated.net/get"
REQUEST_TIMEOUT = 5  # seconds — this runs synchronously in a request/response cycle


def _translate_one(text: str, target_lang_code: str) -> str | None:
    try:
        resp = requests.get(
            MYMEMORY_URL,
            params={"q": text, "langpair": f"en|{target_lang_code}"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        translated = data.get("responseData", {}).get("translatedText")
        # MyMemory returns the source text back unchanged (or an error
        # string embedded in the 200 response) when it doesn't actually
        # know the language pair — treat that as "no translation available".
        if not translated or translated.strip().lower() == text.strip().lower():
            return None
        return translated
    except Exception:
        logger.warning("MyMemory translation failed for lang=%s", target_lang_code, exc_info=True)
        return None


def get_ui_translations(target_lang_code: str) -> dict[str, str]:
    """
    Returns {key: translatedText} for every key in UI_STRINGS, for the given
    language code. English (or an empty/unknown code) returns {} — the
    frontend already has the English strings baked in as fallbacks, so
    there's nothing to override.
    """
    if not target_lang_code or target_lang_code == "en":
        return {}

    result: dict[str, str] = {}
    to_fetch: list[str] = []

    cached = UITranslation.objects(lang_code=target_lang_code)
    cached_by_key = {row.key: row.text for row in cached}

    for key in UI_STRINGS:
        if key in cached_by_key:
            result[key] = cached_by_key[key]
        else:
            to_fetch.append(key)

    for key in to_fetch:
        translated = _translate_one(UI_STRINGS[key], target_lang_code)
        if translated is None:
            continue  # leave this key out — frontend falls back to English
        result[key] = translated
        try:
            UITranslation(
                id=f"{target_lang_code}:{key}", lang_code=target_lang_code, key=key, text=translated
            ).save()
        except Exception:
            logger.exception("Failed to cache translation for %s:%s", target_lang_code, key)

    return result
