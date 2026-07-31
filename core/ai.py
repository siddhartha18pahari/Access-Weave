"""
Provider-neutral language-model adapter.

Default backend is "local": no network, fully deterministic, always available.
This keeps the demo reliable and privacy-preserving. If AI_BACKEND is set to a
provider and a key is present, the adapter may enrich results — but the compiler
never *depends* on it, and every model output is schema-validated before use.
"""
from __future__ import annotations

import json
from django.conf import settings


def backend() -> str:
    return settings.ACCESSWEAVE.get("AI_BACKEND", "local")


def is_local() -> bool:
    return backend() == "local"


def suggest_barriers(text: str) -> list[dict]:
    """Optional model-suggested barriers. Local backend returns []."""
    if is_local():
        return []
    # A real provider call would go here, returning parsed JSON. Kept minimal and
    # defensive: any failure falls back to the deterministic engine.
    try:  # pragma: no cover - only runs when a provider is configured
        raw = _call_provider(_BARRIER_PROMPT.format(text=text[:4000]))
        data = json.loads(raw)
        return data.get("barriers", []) if isinstance(data, dict) else []
    except Exception:
        return []


def rewrite_plain(text: str) -> str | None:
    """Optional model plain-language rewrite. Local backend returns None."""
    if is_local():
        return None
    try:  # pragma: no cover
        return _call_provider(_PLAIN_PROMPT.format(text=text[:4000]))
    except Exception:
        return None


# --- Provider plumbing (only used when configured) --------------------------
_BARRIER_PROMPT = (
    "Identify accessibility barriers in the text. Respond ONLY with JSON: "
    '{{"barriers":[{{"category":"cognition","title":"...","evidence":"...",'
    '"severity":"medium","confidence":0.7,"adaptation":"..."}}]}}. '
    "category must be one of: perception, operation, cognition, communication, "
    "mobility, affordability, availability, suitability, safety, privacy.\n\n{text}"
)
_PLAIN_PROMPT = (
    "Rewrite in plain language at a grade-6 reading level. Keep every number, "
    "unit, and warning EXACTLY as written. Do not add advice.\n\n{text}"
)


def _call_provider(prompt: str) -> str:  # pragma: no cover
    """Placeholder for an approved provider call (e.g. Anthropic Messages API).

    Intentionally not wired to a network by default. Configure AI_BACKEND and
    AI_API_KEY and implement this to enable enrichment.
    """
    raise NotImplementedError("No AI provider configured; using local engine.")
