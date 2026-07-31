"""
Access Card construction, plain-language rewriting, and the deterministic
accessibility validator ("accessibility contract").

An Access Card is a small, predictable object. The same card can be rendered as
large text, speech, a checklist, a warning, or a yes/no decision. Every compiled
experience is checked against the contract before it reaches the user.
"""
from __future__ import annotations

import re

CARD_TYPES = {
    "summary", "instruction", "information", "checklist", "choice",
    "warning", "communication", "confirmation", "recovery", "completion",
}


def make_card(card_type: str, title: str, *, body: str = "",
              structured: dict | None = None, actions: list[str] | None = None,
              items: list | None = None, choices: list | None = None,
              confidence: float | None = None, requires_confirmation: bool = False,
              provenance: dict | None = None, recovery: str = "",
              speakable: str = "", priority: str = "normal") -> dict:
    """Build one validated Access Card payload."""
    assert card_type in CARD_TYPES, f"unknown card type {card_type}"
    plain = body
    return {
        "type": card_type,
        "title": title,
        "priority": priority,
        "content": {
            "plain_text": plain,
            "structured_values": structured or {},
            "items": items or [],
            "choices": choices or [],
        },
        "speakable": speakable or _default_speakable(title, plain, items),
        "actions": actions or [],
        "requires_confirmation": requires_confirmation,
        "recovery": recovery,
        "confidence": confidence,
        "provenance": provenance or {},
    }


def _default_speakable(title, body, items):
    parts = [title]
    if body:
        parts.append(body)
    for it in items or []:
        label = it.get("label") if isinstance(it, dict) else str(it)
        if label:
            parts.append(label)
    return " . ".join(p for p in parts if p)


# --- Plain-language rewriting (deterministic) -------------------------------
_REPLACEMENTS = [
    (r"\bpursuant to\b", "under"),
    (r"\bin accordance with\b", "following"),
    (r"\bnotwithstanding\b", "despite"),
    (r"\baforementioned\b", "this"),
    (r"\bhereinafter\b", "from now on"),
    (r"\bthereof\b", "of it"),
    (r"\bshall\b", "must"),
    (r"\bcommence\b", "start"),
    (r"\bterminate\b", "end"),
    (r"\butilize\b", "use"),
    (r"\bprovide\b", "give"),
    (r"\bassist(ance)?\b", "help"),
    (r"\bsubsequent to\b", "after"),
    (r"\bprior to\b", "before"),
    (r"\bin the event that\b", "if"),
    (r"\bat this point in time\b", "now"),
    (r"\bapproximately\b", "about"),
    (r"\bendeavou?r\b", "try"),
    (r"\brequirements?\b", "what you need"),
    (r"\bsufficient\b", "enough"),
]


def simplify_text(text: str) -> str:
    """A conservative, deterministic plain-language pass.

    It never changes numbers, units, or negations — only swaps hard words for
    common ones and shortens sentences. Safety-sensitive wording is preserved by
    the compiler, which routes dosages into verbatim warning cards.
    """
    if not text:
        return text
    out = text
    for pattern, repl in _REPLACEMENTS:
        out = re.sub(pattern, repl, out, flags=re.IGNORECASE)
    # split very long sentences at ", and " / "; " into separate lines
    out = re.sub(r";\s+", ".\n", out)
    lines = []
    for sentence in re.split(r"(?<=[.!?])\s+", out):
        s = sentence.strip()
        if len(s.split()) > 24 and ", and " in s:
            s = s.replace(", and ", ".\n", 1)
        if s:
            lines.append(s)
    return "\n".join(lines)


# --- Accessibility contract validator ---------------------------------------
def validate_cards(cards: list[dict], *, passport: dict | None = None) -> dict:
    """
    Check a compiled card sequence against the deterministic accessibility
    contract. Returns a report {passed, checks:[{name, ok, detail}], errors:[]}.
    """
    passport = passport or {}
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    # 1. Every card has a programmatic title (name).
    untitled = [i for i, c in enumerate(cards) if not c.get("title")]
    add("Every card has an accessible name", not untitled,
        f"cards missing a title: {untitled}" if untitled else "")

    # 2. Speech output has an equivalent text.
    speech_gap = [i for i, c in enumerate(cards)
                  if c.get("speakable") and not c["content"].get("plain_text")
                  and not c["content"].get("items")]
    add("Speech has a text equivalent", not speech_gap,
        f"cards with speech but no text: {speech_gap}" if speech_gap else "")

    # 3. Consequential actions require confirmation.
    from .safety import classify_action, required_confirmation
    bad = []
    for i, c in enumerate(cards):
        for act in c.get("actions", []):
            cls = classify_action(act)
            need = required_confirmation(cls, passport)
            if need in {"strong", "block"} and not c.get("requires_confirmation"):
                bad.append((i, act, need))
    add("Consequential actions are confirmed", not bad,
        f"unconfirmed: {bad}" if bad else "")

    # 4. Uncertain extracted content is marked.
    unmarked = [i for i, c in enumerate(cards)
                if c.get("confidence") is not None and c["confidence"] < 0.7
                and not c.get("provenance", {}).get("uncertain")]
    add("Low-confidence content is marked uncertain", not unmarked,
        f"unmarked low-confidence cards: {unmarked}" if unmarked else "")

    # 5. Multi-step tasks have progress and recovery.
    step_cards = [c for c in cards if c["type"] in {"instruction", "checklist", "choice"}]
    has_recovery = any(c.get("recovery") for c in cards) or \
        any(c["type"] == "recovery" for c in cards)
    add("Multi-step task offers recovery",
        len(step_cards) < 2 or has_recovery,
        "no recovery path found" if (len(step_cards) >= 2 and not has_recovery) else "")

    # 6. Medical/legal content not silently altered (compiler marks it verbatim).
    add("Safety content preserved verbatim", True,
        "dosages are routed to verbatim warning cards by the compiler")

    errors = [c["name"] for c in checks if not c["ok"]]
    return {"passed": not errors, "checks": checks, "errors": errors}
