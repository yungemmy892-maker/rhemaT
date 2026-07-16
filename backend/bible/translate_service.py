import json
import logging
import re

import requests
from django.conf import settings

from .languages import LANGUAGES
from .models import UITranslation
from .ui_strings import UI_STRINGS

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30  # LLM calls run slower than a dedicated translation API

_LANG_NAMES = {lang["code"]: lang["name"] for lang in LANGUAGES}

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)

_TRANSLATION_PROMPT = """You are translating user interface text for a Bible \
verse-lookup mobile app from English into {lang_name}. Translate each string \
in the JSON array below. Keep translations short and natural, matching the \
tone of app UI text (buttons, labels, short sentences) rather than formal \
prose. Preserve any placeholders or punctuation patterns as-is.

Respond with ONLY a JSON array of the translated strings, in the exact same \
order as the input, with exactly {count} elements. No markdown, no code \
fences, no explanation — just the raw JSON array.

Input:
{items_json}"""


def _parse_json_array(raw: str, expected_len: int) -> list[str] | None:
    cleaned = _CODE_FENCE_RE.sub("", raw.strip()).strip()
    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, list) or len(parsed) != expected_len:
        return None
    if not all(isinstance(item, str) for item in parsed):
        return None
    return parsed


def _translate_batch_gemini(texts: list[str], lang_name: str) -> list[str] | None:
    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not api_key:
        return None

    model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    prompt = _TRANSLATION_PROMPT.format(
        lang_name=lang_name, count=len(texts), items_json=json.dumps(texts, ensure_ascii=False)
    )

    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = _parse_json_array(text, len(texts))
        if result is None:
            logger.warning("Gemini returned unparseable/wrong-shaped response for lang=%s", lang_name)
        return result
    except Exception:
        logger.warning("Gemini translation request failed for lang=%s", lang_name, exc_info=True)
        return None


def _translate_batch_groq(texts: list[str], lang_name: str) -> list[str] | None:
    api_key = getattr(settings, "GROQ_API_KEY", "")
    if not api_key:
        return None

    model = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    prompt = _TRANSLATION_PROMPT.format(
        lang_name=lang_name, count=len(texts), items_json=json.dumps(texts, ensure_ascii=False)
    )

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        result = _parse_json_array(text, len(texts))
        if result is None:
            logger.warning("Groq returned unparseable/wrong-shaped response for lang=%s", lang_name)
        return result
    except Exception:
        logger.warning("Groq translation request failed for lang=%s", lang_name, exc_info=True)
        return None


def _translate_batch(texts: list[str], target_lang_code: str) -> list[str] | None:
    """Translates every string in `texts` in a single call, trying Gemini
    first and falling back to Groq if Gemini is unset or fails."""
    if not texts:
        return None

    lang_name = _LANG_NAMES.get(target_lang_code, target_lang_code)

    result = _translate_batch_gemini(texts, lang_name)
    if result is not None:
        return result

    return _translate_batch_groq(texts, lang_name)


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