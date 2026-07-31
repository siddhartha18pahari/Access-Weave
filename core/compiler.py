"""
The Accessibility Compiler.

Input: a goal, optional source content, the source type, and the user's Access
Passport. Output: a barrier analysis, an explainable task graph, and a validated
sequence of Access Cards.

"Compile, do not merely describe" — the compiler does not just report that
something is inaccessible; it produces an accessible path to completing it.

The engine is deterministic (works offline, is testable, and is explainable). An
optional language model can enrich barriers or plain-language text, but its output
is validated against the approved taxonomy and the accessibility contract before
it can reach the user.
"""
from __future__ import annotations

import re

from . import ai
from .barriers import detect_barriers, merge_model_barriers, TAXONOMY
from .cards import make_card, simplify_text, validate_cards
from .safety import classify_action, required_confirmation, confirmation_prompt


# --- source classification --------------------------------------------------
def classify_source(text: str, goal: str) -> str:
    t = (text or "").lower()
    g = (goal or "").lower()
    medicine_signals = ("capsule", "tablet", "mg", "ml", "dose", "twice daily",
                        "pharmacist", "with food", "prescription")
    form_signals = ("first name", "last name", "date of birth", "address",
                    "signature", "field", "required", "application", "form")
    bill_signals = ("amount due", "amount owing", "invoice", "due date",
                    "balance", "payment due", "account number", "total due",
                    "minimum payment", "overdue")
    appt_signals = ("appointment", "your visit", "clinic", "consultation",
                    "please arrive", "check in", "referral", "scheduled for",
                    "reschedule")
    if sum(s in t for s in medicine_signals) >= 2 or "medic" in g or "label" in g:
        return "medicine"
    if sum(s in t for s in bill_signals) >= 2 or any(w in g for w in ("bill", "invoice", "payment")):
        return "bill"
    if sum(s in t for s in appt_signals) >= 2 or "appointment" in g:
        return "appointment"
    if sum(s in t for s in form_signals) >= 2 or "form" in g or "application" in g:
        return "form"
    if text and len(text.split()) >= 8:
        return "instructions"
    return "goal_only"


def reading_level(text: str) -> int:
    """A rough Flesch–Kincaid grade estimate (no external deps)."""
    words = re.findall(r"[A-Za-z]+", text or "")
    sentences = [s for s in re.split(r"[.!?]+", text or "") if s.strip()]
    if not words or not sentences:
        return 0
    syllables = sum(_syllables(w) for w in words)
    grade = (0.39 * (len(words) / len(sentences))
             + 11.8 * (syllables / len(words)) - 15.59)
    return max(1, round(grade))


def _syllables(word: str) -> int:
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


# --- main entry -------------------------------------------------------------
def compile_task(*, goal: str, source_text: str = "", source_type: str = "text",
                 passport: dict | None = None,
                 ocr_confidence: float | None = None) -> dict:
    passport = passport or {}
    cog = passport.get("cognitive", {})
    plain = cog.get("plain_language", False)

    kind = classify_source(source_text, goal)

    barriers = detect_barriers(source_text, passport=passport,
                               source_type=source_type)
    if not ai.is_local():
        barriers = merge_model_barriers(barriers, ai.suggest_barriers(source_text))

    cards: list[dict] = []
    seq = 0

    def add(card):
        nonlocal seq
        card = dict(card)
        card["sequence"] = seq
        seq += 1
        cards.append(card)

    # 1. Summary card — always first. Sets expectations + provenance + confidence.
    overall_conf = ocr_confidence if ocr_confidence is not None else 0.95
    add(make_card(
        "summary",
        title=f"Your task: {goal}" if goal else "Your task",
        body=_summary_body(kind, barriers),
        structured={"barriers_found": len(barriers),
                    "source": source_type,
                    "reading_level": reading_level(source_text) or "n/a"},
        confidence=overall_conf,
        provenance={"source_type": source_type,
                    "uncertain": overall_conf is not None and overall_conf < 0.7},
        priority="high",
    ))

    # 2. Body cards depend on the kind of source.
    if kind == "medicine":
        _build_medicine(add, source_text, passport, ocr_confidence)
    elif kind == "bill":
        _build_bill(add, source_text, passport)
    elif kind == "appointment":
        _build_appointment(add, source_text, passport)
    elif kind == "form":
        _build_form(add, source_text, goal, passport)
    elif kind == "instructions":
        _build_instructions(add, source_text, passport, plain)
    else:
        _build_from_goal(add, goal, passport, plain)

    # 3. Recovery card for any multi-step task (cognitive support).
    step_like = [c for c in cards if c["type"] in {"instruction", "checklist", "choice"}]
    if len(step_like) >= 2 and cog.get("recovery_instructions", True):
        add(make_card(
            "recovery",
            title="If something goes wrong",
            body=("You can go back one step, pause and resume later, or ask for "
                  "help. Nothing is submitted or shared without your confirmation."),
            actions=["go_back", "pause", "get_help"],
            recovery="Return to the previous step at any time.",
        ))

    # 4. Completion card.
    add(make_card(
        "completion",
        title="You're all set",
        body="You reached the end of this task. You can review any step again, "
             "start a new task, or delete this task and its source now.",
        actions=["review", "new_task", "delete_task"],
    ))

    validation = validate_cards(cards, passport=passport)

    analysis = {
        "kind": kind,
        "summary": _summary_body(kind, barriers),
        "reading_level": reading_level(source_text),
        "confidence": overall_conf,
        "barriers": [b.as_dict() for b in barriers],
        "taxonomy": TAXONOMY,
    }
    task_graph = _build_graph(goal, barriers, cards)

    return {"analysis": analysis, "task_graph": task_graph,
            "cards": cards, "validation": validation}


def _summary_body(kind, barriers):
    label = {
        "medicine": "This looks like a medicine instruction.",
        "bill": "This looks like a bill or payment notice.",
        "appointment": "This looks like an appointment.",
        "form": "This looks like a form.",
        "instructions": "This looks like a set of instructions.",
        "goal_only": "Let's break this goal into clear steps.",
    }[kind]
    if barriers:
        top = ", ".join(sorted({b.category for b in barriers}))
        return f"{label} I noticed possible barriers: {top}. I've turned it into simple steps you can take one at a time."
    return f"{label} I've turned it into simple steps you can take one at a time."


# --- builders ---------------------------------------------------------------
_MED_DOSE = re.compile(
    r"(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten)\s*"
    r"(capsule|tablet|pill|mg|ml|mcg|g|drop|puff|units?)s?", re.I)
_MED_FREQ = re.compile(r"(once|twice|three times|four times|\d+\s*times)\s*(a|per|each)?\s*(day|daily)", re.I)
_MED_MAX = re.compile(r"(do not exceed|no more than|not more than|maximum(?: of)?(?: dose(?: is)?)?)\s+([^.\n]+)", re.I)
_MED_WITH = re.compile(r"with\s+(food|water|milk|a meal)", re.I)
_MED_CONTACT = re.compile(r"(contact|call|ask)\s+([^.\n]*?(pharmacist|doctor|physician)[^.\n]*)", re.I)


def _build_medicine(add, text, passport, ocr_confidence):
    dose = _MED_DOSE.search(text)
    freq = _MED_FREQ.search(text)
    with_what = _MED_WITH.search(text)
    structured = {}
    if dose:
        structured["Take"] = dose.group(0)
    if freq:
        structured["When"] = freq.group(0)
    if with_what:
        structured["With"] = with_what.group(1)

    low_conf = ocr_confidence is not None and ocr_confidence < 0.7
    add(make_card(
        "instruction",
        title="How to take this",
        body="Here is the dose from the label. Please check it against the "
             "package — I only read what was printed.",
        structured=structured or {"Note": "I could not clearly separate the dose."},
        actions=["repeat", "create_reminder"],
        requires_confirmation=required_confirmation("external", passport) in {"strong", "block"},
        confidence=ocr_confidence,
        provenance={"source_type": "label", "uncertain": low_conf},
        recovery="Not sure? Take another photo or ask your pharmacist.",
        priority="high",
    ))

    # Maximum / limit -> its own verbatim warning card (never altered).
    mx = _MED_MAX.search(text)
    if mx:
        add(make_card(
            "warning",
            title="Important limit",
            body=mx.group(0).strip(),  # verbatim source wording
            provenance={"verbatim": True, "source_type": "label"},
            priority="high",
        ))

    # Contact / help.
    contact = _MED_CONTACT.search(text)
    if contact:
        add(make_card(
            "information",
            title="If you need help",
            body=contact.group(0).strip(),
        ))

    # Reminder is an action that AccessWeave prepares but does not auto-run.
    add(make_card(
        "confirmation",
        title="Create a reminder?",
        body="I can create a reminder for this medicine. Nothing is created until "
             "you confirm.",
        structured=confirmation_prompt(
            "Create a medicine reminder", reversible=True,
            recipient="Only you", cost="", shares_data="Stays on your device."),
        actions=["create_reminder"],
        requires_confirmation=True,
    ))


_MONEY = re.compile(r"(?:amount due|total due|balance|amount owing|minimum payment|total)\D{0,20}?([$£€]\s?\d[\d,]*(?:\.\d{2})?)", re.I)
_MONEY_ANY = re.compile(r"([$£€]\s?\d[\d,]*(?:\.\d{2})?)")
_DUE = re.compile(r"(?:due|due date|pay by|payment due)\D{0,15}?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:,?\s*\d{4})?)", re.I)
_ACCOUNT = re.compile(r"account\s*(?:number|no\.?|#)?\s*[:#]?\s*([A-Za-z0-9\-]{4,})", re.I)


def _build_bill(add, text, passport):
    amount = _MONEY.search(text) or _MONEY_ANY.search(text)
    due = _DUE.search(text)
    structured = {}
    if amount:
        structured["Amount due"] = amount.group(1).replace(" ", "")
    if due:
        structured["Pay by"] = due.group(1)
    add(make_card(
        "information",
        title="What this bill says",
        body="Here's what I read. Please check it against the original — I only "
             "read the printed text and never change amounts.",
        structured=structured or {"Note": "I couldn't clearly find the amount or date."},
        actions=["repeat"],
        provenance={"source_type": "bill"},
        priority="high",
    ))
    add(make_card(
        "checklist",
        title="Before you pay",
        body="A quick check so nothing goes wrong:",
        items=[{"label": "Is the amount what you expected?"},
               {"label": "Is this the correct company / account?"},
               {"label": "Do you have until the due date?"},
               {"label": "Choose how you'll pay (online, phone, in person)."}],
        recovery="Not sure it's genuine? Contact the company using details you "
                 "already trust — not just the ones on this notice.",
    ))
    # Paying is a FINANCIAL action — always strongly confirmed, never automatic.
    add(make_card(
        "confirmation",
        title="Ready to pay?",
        body="AccessWeave never makes a payment for you. When you're ready, you "
             "pay through your own bank or the company's official site. I can set "
             "a reminder for the due date.",
        structured=confirmation_prompt(
            "Set a payment reminder", reversible=True, recipient="Only you",
            cost="No cost — this only sets a reminder.",
            shares_data="Stays on your device."),
        actions=["create_reminder"],
        requires_confirmation=True,
        priority="high",
    ))


_APPT_TIME = re.compile(r"\b(\d{1,2}:\d{2}\s?(?:am|pm)?|\d{1,2}\s?(?:am|pm))\b", re.I)
_APPT_DATE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*,?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2}(?:,?\s*\d{4})?)\b", re.I)
_APPT_PLACE = re.compile(r"(?:at|location|address|clinic|office)[:\s]+([A-Z][^.\n,]{4,50})")


def _build_appointment(add, text, passport):
    when_t = _APPT_TIME.search(text)
    when_d = _APPT_DATE.search(text)
    where = _APPT_PLACE.search(text)
    structured = {}
    if when_d:
        structured["Date"] = when_d.group(1)
    if when_t:
        structured["Time"] = when_t.group(1)
    if where:
        structured["Where"] = where.group(1).strip()
    add(make_card(
        "information",
        title="Your appointment",
        body="Here's what I found. Please double-check the date and place.",
        structured=structured or {"Note": "I couldn't clearly find the date/time."},
        actions=["repeat"],
        provenance={"source_type": "appointment"},
        priority="high",
    ))
    add(make_card(
        "checklist",
        title="What to bring & prepare",
        body="A short list so you feel ready:",
        items=[{"label": "ID and any documents or referral letter."},
               {"label": "A list of your questions."},
               {"label": "A list of your medicines, if relevant."},
               {"label": "Plan how you'll get there and how long it takes."}],
        recovery="You can come back to this list any time before you go.",
    ))
    add(make_card(
        "communication",
        title="Phrases you might need",
        body="Tap-to-speak phrases for the appointment:",
        items=[{"label": "Please explain that in plain language."},
               {"label": "Please give me a moment."},
               {"label": "Can a support person join me?"}],
        actions=["open_communication"],
    ))
    add(make_card(
        "confirmation",
        title="Set a reminder?",
        body="I can remind you before the appointment. Nothing is created until "
             "you confirm.",
        structured=confirmation_prompt(
            "Set an appointment reminder", reversible=True, recipient="Only you",
            shares_data="Stays on your device."),
        actions=["create_reminder"],
        requires_confirmation=True,
    ))


def _build_form(add, text, goal, passport):
    fields = _extract_fields(text)
    if not fields:
        fields = ["Your details", "Contact information", "Review and submit"]
    for i, field in enumerate(fields, start=1):
        sensitive = bool(re.search(r"(social security|ssn|passport|date of birth|dob|national id)", field, re.I))
        add(make_card(
            "instruction",
            title=f"Step {i}: {field}",
            body=("This field is sensitive — you never have to store it here, and "
                  "nothing is shared without your confirmation."
                  if sensitive else
                  "Fill this in. I'll explain anything that's unclear and save your progress."),
            actions=["repeat", "next"],
            priority="high" if sensitive else "normal",
            recovery="You can go back and change earlier answers.",
        ))
    # Explicit confirmation before any submission (external action).
    add(make_card(
        "confirmation",
        title="Review before you submit",
        body="Check your answers. AccessWeave never submits a form for you "
             "without this confirmation.",
        structured=confirmation_prompt(
            "Submit this form", reversible=False,
            recipient="The organization that owns the form",
            shares_data="Only what you entered."),
        actions=["submit"],
        requires_confirmation=True,
        priority="high",
    ))


def _build_instructions(add, text, passport, plain):
    steps = _segment_steps(text)
    for i, step in enumerate(steps, start=1):
        body = simplify_text(step) if plain else step
        model_plain = ai.rewrite_plain(step) if (plain and not ai.is_local()) else None
        add(make_card(
            "instruction",
            title=f"Step {i}",
            body=model_plain or body,
            actions=["repeat", "simplify", "next"],
            recovery="You can go back to the previous step.",
        ))


def _build_from_goal(add, goal, passport, plain):
    steps = goal_template(goal)
    for i, step in enumerate(steps, start=1):
        add(make_card(
            "instruction",
            title=f"Step {i}",
            body=simplify_text(step) if plain else step,
            actions=["repeat", "next"],
            recovery="You can go back to the previous step.",
        ))


# --- helpers ----------------------------------------------------------------
def _extract_fields(text):
    fields = []
    for line in (text or "").splitlines():
        line = line.strip(" -*•\t")
        m = re.match(r"([A-Z][A-Za-z /]{2,40})\s*[:*]", line)
        if m:
            fields.append(m.group(1).strip())
        elif re.search(r"(name|address|email|phone|date of birth|signature|"
                       r"income|id number|postcode|zip)", line, re.I) and len(line) < 60:
            fields.append(line)
    # de-dup, cap
    out, seen = [], set()
    for f in fields:
        k = f.lower()
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out[:8]


def _segment_steps(text):
    text = text or ""
    # explicit numbered / bulleted list?
    items = re.findall(r"(?m)^\s*(?:\d+[.)]|[-*•])\s+(.*\S)", text)
    if len(items) >= 2:
        return [i.strip() for i in items]
    # otherwise split into sentences and group
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    return sentences if sentences else [text.strip()]


_GOAL_TEMPLATES = {
    "appointment": [
        "Confirm the date, time, and place of your appointment.",
        "Note what to bring: ID, any documents, and a list of your questions.",
        "Plan how you will get there and how long it takes.",
        "Prepare a few communication phrases in case you need them.",
        "Decide who you can contact if the appointment is delayed or changed.",
    ],
    "transit": [
        "Confirm which transit agency you need.",
        "Open the renewal page and turn on simplified view.",
        "Gather the information you'll need before you start.",
        "Fill one section at a time; your progress is saved after each.",
        "Check the total cost before paying.",
        "Confirm explicitly before any payment.",
        "Save your receipt where you can find it.",
    ],
    "phone": [
        "Write down exactly what you need to ask or say.",
        "Check whether there is a text, email, or online option instead of calling.",
        "If you must call, prepare short phrases you can read aloud or have spoken.",
        "Have a pen and paper ready to note the answer.",
        "Ask them to repeat or write down anything important.",
    ],
    "cooking": [
        "Gather every ingredient and tool before you start.",
        "Read all the steps once so there are no surprises.",
        "Set out what you need for the first step only.",
        "Do one step at a time; I'll read the next when you're ready.",
        "Turn off heat and appliances when you finish.",
    ],
    "shopping": [
        "Make a list of exactly what you need.",
        "Check what you already have at home first.",
        "Decide your budget before you go or order.",
        "Confirm the total cost before you pay — nothing is bought without you.",
        "Keep the receipt in case you need to return something.",
    ],
    "writing": [
        "Name who this message is for and what you want to happen.",
        "Say the main point in one plain sentence.",
        "Add only the details they truly need.",
        "Read it back (or have it read aloud) to check the tone.",
        "You confirm before anything is sent — I never send for you.",
    ],
    "setup": [
        "Open Settings, then Accessibility, on your device.",
        "Choose the tool you want: text size, contrast, speech, or voice control.",
        "Turn it on and try it right away with one small task.",
        "Adjust the level until it feels right for you.",
        "If it doesn't help, you can turn it off — nothing is permanent.",
    ],
    "email": [
        "Open your email and find the message you need.",
        "Have it read aloud or enlarged so you don't miss anything.",
        "Note any date, amount, or action it asks for.",
        "Draft a short, clear reply — one point per sentence.",
        "You confirm before sending — I never send on your behalf.",
    ],
}


def goal_template(goal: str):
    g = (goal or "").lower()
    if any(w in g for w in ("appointment", "doctor", "clinic", "visit")):
        return _GOAL_TEMPLATES["appointment"]
    if any(w in g for w in ("transit", "pass", "renew", "ticket", "bus", "train")):
        return _GOAL_TEMPLATES["transit"]
    if any(w in g for w in ("call", "phone", "ring")):
        return _GOAL_TEMPLATES["phone"]
    if any(w in g for w in ("cook", "recipe", "bake", "meal", "make food", "dinner")):
        return _GOAL_TEMPLATES["cooking"]
    if any(w in g for w in ("shop", "buy", "groceries", "order", "purchase")):
        return _GOAL_TEMPLATES["shopping"]
    if any(w in g for w in ("email", "inbox", "reply to")):
        return _GOAL_TEMPLATES["email"]
    if any(w in g for w in ("write", "message", "letter", "text", "compose")):
        return _GOAL_TEMPLATES["writing"]
    if any(w in g for w in ("set up", "setup", "settings", "accessibility", "turn on", "enable", "configure")):
        return _GOAL_TEMPLATES["setup"]
    return [
        "Let's name exactly what 'done' looks like for this task.",
        "List what you already have and what you still need.",
        "Do the first small part now; the rest can wait.",
        "Check your work before anything is sent or shared.",
        "Decide if you want a reminder or someone to help.",
    ]


def _build_graph(goal, barriers, cards):
    nodes = [{"id": "goal", "type": "goal", "label": goal or "Your task"}]
    edges = []
    for i, b in enumerate(barriers):
        bid = f"barrier_{i}"
        nodes.append({"id": bid, "type": "barrier", "label": b.title,
                      "category": b.category})
        edges.append({"from": "goal", "rel": "HAS_BARRIER", "to": bid})
        if b.adaptation:
            aid = f"adapt_{i}"
            nodes.append({"id": aid, "type": "adaptation", "label": b.adaptation})
            edges.append({"from": bid, "rel": "ADAPTED_BY", "to": aid})
    step_cards = [c for c in cards if c["type"] in {"instruction", "checklist", "choice"}]
    for i, c in enumerate(step_cards):
        sid = f"step_{i}"
        nodes.append({"id": sid, "type": "step", "label": c["title"]})
        edges.append({"from": "goal", "rel": "HAS_STEP", "to": sid})
    return {"nodes": nodes, "edges": edges}
