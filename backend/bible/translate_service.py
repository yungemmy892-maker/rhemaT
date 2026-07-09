"""
Translates VerseID's UI chrome strings into the user's chosen interface
language, via the Google Cloud Translation API (v2 — the simple REST API,
not the newer Advanced/v3 API, since v2 needs only an API key rather than a
full service-account setup).

Requires GOOGLE_TRANSLATE_API_KEY: a Google Cloud API key with the "Cloud
Translation API" enabled on its project. Unlike Google OAuth
(GOOGLE_CLIENT_ID/SECRET, used for sign-in), this is a separate credential
even if you reuse the same GCP project — see the setup steps in this
module's accompanying documentation.

NOT free at any real scale: Google Cloud Translation gives the first
500,000 characters/month free, then bills per character past that. UI_STRINGS
is small (a few thousand characters total) and every (language, key) pair is
translated at MOST ONCE EVER — cached permanently in Mongo afterward — so
in practice this stays well within the free tier even with many interface
languages enabled, but it does require billing to be enabled on the GCP
project for the API to work at all (Google requires this even to use the
free quota).

When GOOGLE_TRANSLATE_API_KEY is unset, the language isn't recognised, or
the API call fails for any reason, this falls back to the English source
string for that key rather than surfacing an error — a partially-translated
screen (or an all-English one) is a much better experience than a broken
Settings page.
"""
import logging

import requests
from django.conf import settings

from .models import UITranslation
from .ui_strings import UI_STRINGS

logger = logging.getLogger(__name__)

TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"
REQUEST_TIMEOUT = 10  # a full batch of ~30 short strings in one request


def _translate_batch(texts: list[str], target_lang_code: str) -> list[str] | None:
    """Translates every string in `texts` in a single API call — Google
    Translate v2 accepts multiple `q` params and returns translations in
    the same order, so there's no need for one request per string."""
    api_key = getattr(settings, "GOOGLE_TRANSLATE_API_KEY", "")
    if not api_key or not texts:
        return None

    try:
        resp = requests.post(
            TRANSLATE_URL,
            params={"key": api_key},
            json={"q": texts, "target": target_lang_code, "source": "en", "format": "text"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        translations = resp.json()["data"]["translations"]
        if len(translations) != len(texts):
            logger.warning("Google Translate returned %d results for %d inputs", len(translations), len(texts))
            return None
        return [t["translatedText"] for t in translations]
    except Exception:
        logger.warning("Google Translate request failed for lang=%s", target_lang_code, exc_info=True)
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

    cached = UITranslation.objects(lang_code=target_lang_code)
    cached_by_key = {row.key: row.text for row in cached}

    missing_keys = [key for key in UI_STRINGS if key not in cached_by_key]
    result.update(cached_by_key)

    if missing_keys:
        translated_texts = _translate_batch([UI_STRINGS[k] for k in missing_keys], target_lang_code)
        if translated_texts is not None:
            for key, translated in zip(missing_keys, translated_texts):
                result[key] = translated
                try:
                    UITranslation(
                        id=f"{target_lang_code}:{key}",
                        lang_code=target_lang_code,
                        key=key,
                        text=translated,
                    ).save()
                except Exception:
                    logger.exception("Failed to cache translation for %s:%s", target_lang_code, key)

    return {k: v for k, v in result.items() if k in UI_STRINGS}