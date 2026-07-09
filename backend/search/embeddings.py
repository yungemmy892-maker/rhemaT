import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

HF_MODEL = "BAAI/bge-small-en-v1.5"
HF_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}/pipeline/feature-extraction"
REQUEST_TIMEOUT = 30  # precompute sends much larger batches than a live query


def get_embeddings(texts: list[str]) -> list[list[float]] | None:
    """
    Returns one embedding vector per input string, same order — or None if
    embeddings aren't available right now for any reason (no token
    configured, API error, timeout, rate limit, etc).
    """
    token = getattr(settings, "HF_API_TOKEN", "")
    if not token or not texts:
        return None

    try:
        resp = requests.post(
            HF_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": texts, "options": {"wait_for_model": True}},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        vectors = resp.json()
        if not isinstance(vectors, list) or len(vectors) != len(texts):
            logger.warning("Unexpected HF feature-extraction response shape: %r", vectors)
            return None
        return vectors
    except Exception:
        logger.warning("HF embeddings request failed", exc_info=True)
        return None