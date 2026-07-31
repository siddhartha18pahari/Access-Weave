"""
Safe Autonomy Engine (policy layer).

AccessWeave can *prepare* actions but must not silently take control. This module
classifies actions and computes the required confirmation strength. The platform
enforces a *floor*: a user's passport can make confirmation stricter, never
weaker. Medical actions are always blocked from autonomous execution.
"""
from __future__ import annotations

# action class -> platform minimum confirmation ("standard" < "strong" < "block")
PLATFORM_FLOOR = {
    "informational": "none",
    "reversible": "none",
    "external": "strong",
    "financial": "strong",
    "medical": "block",
    "legal": "strong",
    "location": "strong",
    "supporter": "strong",
}

_ORDER = {"none": 0, "standard": 1, "strong": 2, "block": 3}

# Map passport safety keys to action classes.
_PASSPORT_KEY = {
    "external": "external_action",
    "financial": "financial_action",
    "medical": "medical_action",
    "legal": "legal_action",
}


def required_confirmation(action_class: str, passport: dict | None = None) -> str:
    """Return the confirmation level to enforce for an action class."""
    action_class = (action_class or "informational").lower()
    floor = PLATFORM_FLOOR.get(action_class, "strong")
    passport = passport or {}
    safety = passport.get("safety", {})
    key = _PASSPORT_KEY.get(action_class)
    user_pref = safety.get(key) if key else None
    # take the stricter of platform floor and user preference
    level = floor
    if user_pref and _ORDER.get(user_pref, 0) > _ORDER.get(level, 0):
        level = user_pref
    return level


def classify_action(text: str) -> str:
    """Heuristically classify a proposed action from its description."""
    t = (text or "").lower()
    if any(w in t for w in ("dose", "medication", "medicine", "prescription",
                            "diagnos", "treatment")):
        return "medical"
    if any(w in t for w in ("pay", "payment", "purchase", "buy", "subscribe",
                            "charge", "$", "fee")):
        return "financial"
    if any(w in t for w in ("submit", "send", "share", "book", "apply",
                            "transmit", "post", "email")):
        return "external"
    if any(w in t for w in ("consent", "legal", "declaration", "sign")):
        return "legal"
    if "location" in t:
        return "location"
    if any(w in t for w in ("notify supporter", "alert supporter", "support circle")):
        return "supporter"
    if any(w in t for w in ("draft", "fill", "prepare", "checklist")):
        return "reversible"
    return "informational"


def confirmation_prompt(action_desc: str, *, reversible: bool,
                        recipient: str = "", cost: str = "",
                        shares_data: str = "") -> dict:
    """Build the content of a confirmation card. A confirmation must state
    what will happen, who receives info, reversibility, cost and shared data."""
    return {
        "action": action_desc,
        "reversible": reversible,
        "recipient": recipient or "No one — this stays on your device.",
        "cost": cost or "No cost.",
        "shares_data": shares_data or "No personal data is shared.",
    }
