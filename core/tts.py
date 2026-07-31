"""
High-quality text-to-speech via ElevenLabs (optional).

If ELEVENLABS_API_KEY is set, `synthesize()` returns MP3 bytes for a short piece
of text. If the key is absent or the call fails, it returns None and the frontend
falls back to the browser's built-in speech synthesis — so voice output always
works, with or without a paid key. The API key stays on the server; the browser
never sees it (requests are proxied through Django).
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error

from django.conf import settings

_API = "https://api.elevenlabs.io/v1/text-to-speech/{voice}"
MAX_CHARS = 800  # keep requests small (latency + free-tier friendly)


def is_enabled() -> bool:
    return bool(settings.ACCESSWEAVE.get("ELEVENLABS_API_KEY"))


def synthesize(text: str) -> bytes | None:
    """Return MP3 bytes for `text`, or None to signal 'use the browser voice'."""
    cfg = settings.ACCESSWEAVE
    key = cfg.get("ELEVENLABS_API_KEY")
    if not key or not text:
        return None
    text = text.strip()[:MAX_CHARS]
    url = _API.format(voice=cfg.get("ELEVENLABS_VOICE_ID"))
    body = json.dumps({
        "text": text,
        "model_id": cfg.get("ELEVENLABS_MODEL", "eleven_turbo_v2_5"),
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "xi-api-key": key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    })
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.status == 200:
                return resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return None
    return None
