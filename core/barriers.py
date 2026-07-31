"""
Barrier taxonomy and deterministic barrier detection.

The Barrier Translator names *why a task is hard* in plain language, with
evidence, a confidence, and — crucially — a concrete adaptation. Detection is
deterministic and rule-based so it works offline and is fully explainable. An
optional language model can add nuance, but every model-produced barrier code is
validated against this approved taxonomy; unknown codes are rejected.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict

# --- Approved taxonomy ------------------------------------------------------
TAXONOMY = {
    "perception": "Perception — small print, low contrast, unclear audio",
    "operation": "Operation — mouse-only, small targets, complex gestures, timeouts",
    "cognition": "Cognition — dense language, too many choices, unclear sequence",
    "communication": "Communication — phone-only, rapid conversation, no text option",
    "mobility": "Mobility — inaccessible route, unknown entrance, no rest point",
    "affordability": "Affordability — high out-of-pocket cost",
    "availability": "Availability — product or service not available nearby",
    "suitability": "Suitability — available support does not fit functional needs",
    "safety": "Safety — medication ambiguity, hazard, uncertain emergency step",
    "privacy": "Privacy — unnecessary data request, forced disclosure",
}

VALID_CATEGORIES = set(TAXONOMY)


@dataclass
class Barrier:
    category: str
    title: str
    evidence: str
    severity: str = "medium"  # low | medium | high
    confidence: float = 0.8
    adaptation: str = ""
    requires_user_verification: bool = False

    def as_dict(self):
        return asdict(self)


# --- Signals ----------------------------------------------------------------
_DENSE_WORDS = re.compile(
    r"\b(pursuant|aforementioned|notwithstanding|hereinafter|thereof|"
    r"heretofore|whereas|shall|deemed|stipulated|in accordance with|"
    r"subject to the provisions)\b",
    re.IGNORECASE,
)
_SAFETY_VALUE = re.compile(
    r"\b(\d+(\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
    r"(mg|ml|mcg|grams?|g|capsules?|tablets?|pills?|doses?|units?|iu|drops?|puffs?)\b",
    re.IGNORECASE,
)
_MAX_LIMIT = re.compile(r"\b(do not exceed|maximum|no more than|not more than)\b", re.I)
_PHONE_ONLY = re.compile(r"\b(call|phone|by telephone|dial)\b", re.IGNORECASE)
_TIMED = re.compile(r"\b(within \d+ (minutes|seconds|hours)|before .* expires|session will time out|timed)\b", re.I)
_PII = re.compile(
    r"\b(social security|ssn|passport number|date of birth|dob|aadhaar|"
    r"national id|mother's maiden name)\b",
    re.IGNORECASE,
)


def _avg_sentence_length(text: str) -> float:
    sentences = [s for s in re.split(r"[.!?\n]+", text) if s.strip()]
    if not sentences:
        return 0.0
    words = sum(len(s.split()) for s in sentences)
    return words / len(sentences)


def detect_barriers(text: str, *, passport: dict | None = None,
                    source_type: str = "text") -> list[Barrier]:
    """Return deterministic barriers found in `text` given the user's passport."""
    text = text or ""
    passport = passport or {}
    cog = passport.get("cognitive", {})
    out: list[Barrier] = []

    # Cognition: dense / legalistic language.
    long_sentences = _avg_sentence_length(text) >= 22
    if _DENSE_WORDS.search(text) or long_sentences:
        out.append(Barrier(
            category="cognition",
            title="Dense or complex language",
            evidence=(_first_match(_DENSE_WORDS, text)
                      or "Long sentences make the meaning hard to follow."),
            severity="high" if cog.get("plain_language") else "medium",
            confidence=0.82,
            adaptation="Rewrite each part in plain language, one idea per line.",
        ))

    # Cognition: many choices / unclear sequence.
    bullet_like = len(re.findall(r"(?m)^\s*(?:[-*•]|\d+[.)])\s+", text))
    if bullet_like >= 6:
        out.append(Barrier(
            category="cognition",
            title="Many steps or options at once",
            evidence=f"Found {bullet_like} list items presented together.",
            severity="medium",
            confidence=0.7,
            adaptation="Present one step at a time with a progress indicator.",
        ))

    # Safety: dosage / units present -> preserve source wording, verify values.
    if _SAFETY_VALUE.search(text):
        m = _SAFETY_VALUE.search(text)
        out.append(Barrier(
            category="safety",
            title="Safety-sensitive value detected",
            evidence=f"Contains a value like “{m.group(0)}”.",
            severity="high",
            confidence=0.9,
            adaptation=("Show the exact source wording. Ask you to confirm the "
                        "number. Never change a dose."),
            requires_user_verification=True,
        ))
    if _MAX_LIMIT.search(text):
        out.append(Barrier(
            category="safety",
            title="Maximum / limit instruction",
            evidence=_first_match(_MAX_LIMIT, text) or "A limit is stated.",
            severity="high",
            confidence=0.85,
            adaptation="Highlight the limit as its own warning card.",
        ))

    # Communication: phone-only contact path.
    if _PHONE_ONLY.search(text):
        out.append(Barrier(
            category="communication",
            title="Phone-dependent step",
            evidence=_first_match(_PHONE_ONLY, text) or "Requires a phone call.",
            severity="medium",
            confidence=0.6,
            adaptation="Offer a text-based alternative and a prepared script.",
        ))

    # Operation: timed step.
    if _TIMED.search(text):
        out.append(Barrier(
            category="operation",
            title="Time limit on a step",
            evidence=_first_match(_TIMED, text) or "A timed step is present.",
            severity="medium",
            confidence=0.7,
            adaptation="Explain the timing up front; allow save-and-resume.",
        ))

    # Privacy: sensitive data request.
    if _PII.search(text):
        out.append(Barrier(
            category="privacy",
            title="Sensitive personal data requested",
            evidence=_first_match(_PII, text) or "Asks for sensitive identifiers.",
            severity="high",
            confidence=0.8,
            adaptation=("Flag which fields are sensitive and remind you these are "
                        "never stored or shared without confirmation."),
        ))

    # Perception: image source implies possible small text / OCR uncertainty.
    if source_type in {"image", "camera", "pdf"}:
        out.append(Barrier(
            category="perception",
            title="Printed text on an image",
            evidence="Text was read from an image, which can be small or blurry.",
            severity="medium",
            confidence=0.6,
            adaptation="Read aloud, enlarge, and mark any uncertain characters.",
        ))

    return out


def merge_model_barriers(deterministic: list[Barrier],
                         model_barriers: list[dict]) -> list[Barrier]:
    """Accept model-suggested barriers only if their category is approved."""
    out = list(deterministic)
    seen = {(b.category, b.title.lower()) for b in deterministic}
    for mb in model_barriers or []:
        cat = str(mb.get("category", "")).lower()
        if cat not in VALID_CATEGORIES:
            continue  # reject unknown codes
        key = (cat, str(mb.get("title", "")).lower())
        if key in seen:
            continue
        out.append(Barrier(
            category=cat,
            title=str(mb.get("title", ""))[:120],
            evidence=str(mb.get("evidence", ""))[:280],
            severity=mb.get("severity", "medium"),
            confidence=float(mb.get("confidence", 0.6)),
            adaptation=str(mb.get("adaptation", ""))[:280],
            requires_user_verification=bool(mb.get("requires_user_verification")),
        ))
        seen.add(key)
    return out


def _first_match(pattern: re.Pattern, text: str) -> str:
    m = pattern.search(text or "")
    if not m:
        return ""
    start = max(0, m.start() - 30)
    end = min(len(text), m.end() + 30)
    snippet = text[start:end].strip().replace("\n", " ")
    return f"…{snippet}…"
