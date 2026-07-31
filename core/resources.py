"""
Assistive Resource Matcher.

Connects a user's functional goal to categories of assistive adaptations,
products, services, and funding pathways. It does NOT diagnose, prescribe, or
guarantee eligibility. Every recommendation is explainable (why it helps, which
barrier it addresses), lists alternatives and limitations, carries a verification
date, and prefers low- and no-cost options first.

The population signal is a small, self-contained, de-identified aggregate used
only to *rank* general categories. It never profiles an individual. (This build
is standalone and does not connect to any external survey database.)
"""
from __future__ import annotations

from datetime import date

VERIFIED_ON = "2026-07-20"

# category -> resource entry
RESOURCE_GRAPH = {
    "voice_access": {
        "label": "Voice access (control your device by speaking)",
        "barriers": ["operation", "mobility"],
        "goals": ["phone", "dexterity", "hands", "type", "tap"],
        "cost_band": "free",
        "why": "Lets you operate labelled on-screen controls without repeated tapping.",
        "prerequisites": ["A device with voice control built in"],
        "training": "About 15 minutes to learn the main commands.",
        "alternatives": ["Switch access", "External keyboard", "Larger touch targets"],
        "limitations": ["May be unsuitable in noisy or private settings."],
        "pathways": ["Built into most phones and computers (Settings > Accessibility)"],
    },
    "switch_access": {
        "label": "Switch access",
        "barriers": ["operation", "mobility"],
        "goals": ["dexterity", "hands", "one button", "scanning"],
        "cost_band": "low",
        "why": "Provides an alternative input pathway using one or two buttons.",
        "prerequisites": ["A compatible switch device"],
        "training": "Setup and practice over a few sessions.",
        "alternatives": ["Voice access", "Dwell selection"],
        "limitations": ["Slower for long text entry."],
        "pathways": ["Assistive-technology provider", "Some public disability programs"],
    },
    "screen_magnifier": {
        "label": "Screen magnification and large text",
        "barriers": ["perception"],
        "goals": ["low vision", "small text", "read", "see"],
        "cost_band": "free",
        "why": "Enlarges text and interface elements for easier reading.",
        "prerequisites": [],
        "training": "A few minutes.",
        "alternatives": ["Screen reader", "High-contrast mode"],
        "limitations": ["Very high zoom can hide layout context."],
        "pathways": ["Built into most operating systems"],
    },
    "screen_reader": {
        "label": "Screen reader (spoken interface)",
        "barriers": ["perception"],
        "goals": ["blind", "low vision", "read aloud"],
        "cost_band": "free",
        "why": "Reads on-screen content and controls aloud so you can navigate by listening.",
        "prerequisites": [],
        "training": "Learning the gestures/keys takes practice.",
        "alternatives": ["Magnification", "Braille display"],
        "limitations": ["Poorly labelled apps can be hard to use."],
        "pathways": ["Built into most operating systems", "Free open-source options"],
    },
    "aac_board": {
        "label": "Communication board / AAC",
        "barriers": ["communication"],
        "goals": ["speak", "communicate", "nonverbal", "aac", "talk"],
        "cost_band": "free",
        "why": "Lets you communicate with prepared phrases, symbols, and speech output.",
        "prerequisites": [],
        "training": "Grows with use; start with a few key phrases.",
        "alternatives": ["Text-to-speech", "Symbol cards"],
        "limitations": ["Prepared phrases can't cover every situation."],
        "pathways": ["AccessWeave Communication Bridge", "Speech-language professional"],
    },
    "captions": {
        "label": "Live captions",
        "barriers": ["communication", "perception"],
        "goals": ["deaf", "hard of hearing", "hearing", "caption", "transcribe"],
        "cost_band": "free",
        "why": "Turns spoken words into text you can read in real time.",
        "prerequisites": ["A device microphone"],
        "training": "None.",
        "alternatives": ["Written notes", "Text chat"],
        "limitations": ["Accuracy drops with background noise or crosstalk."],
        "pathways": ["Built into many phones and browsers"],
    },
    "plain_language": {
        "label": "Plain-language rewriting",
        "barriers": ["cognition"],
        "goals": ["understand", "confusing", "complex", "reading", "form"],
        "cost_band": "free",
        "why": "Rewrites dense text into short, clear sentences you can act on.",
        "prerequisites": [],
        "training": "None.",
        "alternatives": ["Step-by-step mode", "Read aloud"],
        "limitations": ["Simplification can lose legal nuance — keep the original."],
        "pathways": ["AccessWeave Accessibility Compiler"],
    },
}

# Self-contained illustrative aggregate (NOT individual data). Higher = more
# commonly reported as an unmet need in the reference population sample.
_POPULATION_WEIGHT = {
    "perception": 0.82,
    "communication": 0.74,
    "operation": 0.68,
    "cognition": 0.61,
    "mobility": 0.58,
    "affordability": 0.9,
}

_COST_RANK = {"free": 0, "low": 1, "medium": 2, "high": 3}


def match(goal: str, barriers: list[str] | None = None, *,
          affordability_pressure: bool = False) -> dict:
    """Return ranked, explainable recommendations for a goal + barrier set."""
    goal_l = (goal or "").lower()
    barriers = [b.lower() for b in (barriers or [])]
    scored = []
    for key, r in RESOURCE_GRAPH.items():
        score = 0.0
        reasons = []
        for b in barriers:
            if b in r["barriers"]:
                score += 2.0 + _POPULATION_WEIGHT.get(b, 0.5)
                reasons.append(f"addresses a {b} barrier")
        for kw in r["goals"]:
            if kw in goal_l:
                score += 1.5
                reasons.append(f"matches your goal (“{kw}”)")
        if score <= 0:
            continue
        # low-cost-first: reward cheaper options, extra when affordability is a pressure
        cost_penalty = _COST_RANK.get(r["cost_band"], 2)
        score -= cost_penalty * (0.9 if affordability_pressure else 0.4)
        scored.append((score, key, r, reasons))

    scored.sort(key=lambda x: (-x[0], _COST_RANK.get(x[2]["cost_band"], 2)))

    recommendations = []
    for score, key, r, reasons in scored[:5]:
        recommendations.append({
            "id": key,
            "label": r["label"],
            "why": r["why"],
            "because": reasons or ["relevant to your goal"],
            "cost_band": r["cost_band"],
            "prerequisites": r["prerequisites"],
            "training": r["training"],
            "alternatives": r["alternatives"],
            "limitations": r["limitations"],
            "pathways": r["pathways"],
            "confidence": round(min(0.95, 0.5 + score / 10), 2),
            "verified_on": VERIFIED_ON,
        })

    return {
        "recommendations": recommendations,
        "disclaimer": (
            "These are general categories, not medical advice or a guarantee of "
            "eligibility. Population patterns inform ranking only — they never "
            "determine what is right for you as an individual."),
        "population_note": (
            "Ranking gives a small nudge to categories most commonly reported as "
            "unmet needs and to low-cost options. This is de-identified aggregate "
            "context, not your data."),
    }
