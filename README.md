# AccessWeave

### The adaptive independence copilot — *turn any inaccessible task into a personalized, accessible path to completion.*

Built for the **Assistive Innovation Challenge 2026**.

AccessWeave is a privacy-first assistive web app for people with disabilities. Point
it at a medicine label, paste a confusing form, or just describe a goal — it finds
the **barriers**, then **recompiles** the task into clear, accessible **Access Cards**
in *your* preferred format: large text, speech, plain language, one step at a time.

It never asks *“what is your diagnosis?”* It asks **“what would make this task
accessible to you?”**

---

## Why it's different

Most assistive tools solve one modality — a screen reader reads, OCR extracts, a
captioner transcribes — and leave the disabled person to stitch them together.
AccessWeave treats accessibility as an **end-to-end task-completion problem** and
applies one idea:

> **Accessibility as compilation.** Don't just *describe* that something is
> inaccessible — *compile* it into an accessible path.

```
Dense form + small text + timed session   →   Large step cards + plain language
+ mouse-only controls                          + keyboard-first + saved progress
(source)                                        + explicit confirmation (output)
             ↑ constrained by your Access Passport ↑
```

## What it does

### Understand something you're stuck on
| Capability | Detail |
|---|---|
| **Barrier Translator** | Names *why* something is hard — dense language, small print, ambiguous steps, safety-sensitive values, sensitive data — with **evidence, confidence, and a concrete adaptation**. |
| **Accessibility Compiler** | Rebuilds it into validated **Access Cards**. Recognises **medicine labels, bills, appointment letters, forms, and free instructions**, plus goal templates for appointments, transit, phone calls, cooking, shopping, writing, email, and device setup. |
| **Five ways in** | **Speak** a goal · **photograph** a label (read on-device) · **paste** a web address · **paste/type** text · pick an example. |
| **Web Page Reader** | Give it a URL; it fetches the page, strips nav/ads/scripts, and rebuilds just the content as steps. SSRF-guarded. |
| **Task player** | One step at a time, progress, read-aloud, "simpler wording", back/next, pause/resume, refresh recovery. |
| **"Why these steps?"** | Full transparency: the barrier analysis, task graph, and accessibility-contract check. |
| **Routines** | Save a repeatable task (morning meds, leaving the house) and re-run it any time. |

### See, hear, and be heard
| Capability | Detail |
|---|---|
| **Look around** | Point the camera; hear what's in front of you with position — *"a person on your left, a chair ahead, 2 cups on your right."* Live on-device detection; no video leaves the device. |
| **Sound Watch** | For Deaf/HoH users: watches for a doorbell, alarm, or knock and alerts **visually, by vibration, and by system notification**. **Keeps working in background tabs.** One slow pulse, never a strobe. |
| **Conversation Mode** | They speak → big live captions. You reply with phrases or typed text, spoken aloud or shown full-screen. Transcript never stored. |
| **Communication Bridge** | Quick phrase packs, text-to-speech, partner card, and a "please give me more time" button. |

### Control it however you can
| Capability | Detail |
|---|---|
| **Voice control** | A 🎙 button on every screen (or **Alt+V**). Navigate, operate *any* control ("click …"), read the page, adjust the display, complete tasks, and hear a recap — entirely by speaking. |
| **Switch scanning** | A highlight steps through the controls; **any key, click, or game-controller button** selects. Adapted switches work with no drivers. |
| **Dwell selection** | Rest the pointer (or a head/eye tracker) on a control; a countdown ring fills, then it activates. |
| **Command palette** | **Ctrl/⌘+K** — every feature from a few keystrokes. |
| **Shortcut sheet** | Press **?** for all shortcuts. |
| **Focus mode** | **Alt+F** quiets everything except the task. |

### Yours, and private
| Capability | Detail |
|---|---|
| **Access Passport** | A portable profile of *preferences, not diagnoses*. Personalizes the whole UI through CSS design tokens; keep several (Regular, Low-energy…). |
| **Portable Pass (QR)** | Show your passport as a QR code so preferences travel to another device; import is schema-validated. Generated locally. |
| **Resource Matcher** | Explainable, low-cost-first suggestions — why it helps, alternatives, limitations, pathways, verification date. |
| **Privacy controls** | No-storage mode, delete task, delete everything, provenance labels, confidence badges, confirmation before consequential actions, and a fully local fallback. |

## Built to be relied on

Voice output is **queued** so nothing cuts off; speech recognition runs
**continuously and auto-restarts**; voice state **persists across page loads**;
Sound Watch detection runs on the **audio thread** so it survives tab switches;
and **every spoken command has an equivalent on-screen control — nothing is
voice-only, and nothing is JavaScript-only.**

**Natural voice (optional):** set `ELEVENLABS_API_KEY` (the free tier works) and
the app speaks with ElevenLabs' TTS, proxied through the server so the key never
reaches the browser. Without a key it uses the browser's built-in speech — voice
output always works either way.

## Simple, calm, readable interface

The signed-in home is a plain **hub of large tiles** (Start a task, Look around,
Conversation, My tasks, Sound Watch, Communicate, Find support, Passport,
Privacy). Generous spacing, one clear action per tile, a consistent SVG icon set,
and reading/display options tucked into a single tidy menu. Turning on
**reduced-choice mode** trims the hub to the essentials.

Typography uses **Atkinson Hyperlegible** — a typeface the Braille Institute
designed to maximise character distinction for low-vision readers — vendored
locally so it works offline. Lines are capped at a readable measure, with tuned
letter/word spacing and line height, following WCAG 2.2 and public accessibility
guidance for readable, low-clutter pages.

## Safety & privacy, by design

- **No diagnosis is ever required.** The passport holds functional preferences.
- **Uploads are processed in memory and not stored** by default.
- **Medical actions are never automatic**; dosages/warnings are shown **verbatim**.
- **Uncertain, machine-read content is flagged** for you to verify.
- **Consequential actions require confirmation** — enforced by a policy *floor* a
  passport can strengthen but never weaken (see `core/safety.py`).
- **Runs fully offline / with no paid API** — the engine is deterministic.

## Accessible itself (WCAG 2.2 AA target)

Every page works **keyboard-only and without JavaScript**; JS only enhances it.
Skip link, semantic landmarks, visible focus, no color-only status, text resizing
to 300%, reflow with no horizontal scroll, reduced-motion + high-contrast +
light/dark themes, screen-reader announcements, and a quick personalization
toolbar. Installable **PWA** with an offline shell and service worker.

---

## Quick start

```bash
cd accessweave
pip install -r requirements.txt      # just Django + pydantic are required
python manage.py migrate
python manage.py seed_demo           # creates demo account + a sample task
python manage.py runserver
```

Open http://127.0.0.1:8000 and log in with **demo / accessweave**.

> The app runs with **only Django installed**. Pillow, reportlab, and Tesseract
> OCR are optional and degrade gracefully (paste-text is the primary input path).

## Run the tests

```bash
python manage.py test core          # 36 tests: compiler, safety, state, ownership, privacy
```

## Deploy with Docker

```bash
docker compose up --build           # builds, migrates, seeds, serves on :8000 via gunicorn
```

Single container, SQLite on a persisted volume, static served by WhiteNoise. Set
`ELEVENLABS_API_KEY` in the environment (or a `.env`) to enable natural voice.

## Continuous integration

`.github/workflows/ci.yml` runs on every push: the Django test suite, plus an
**axe-core (WCAG 2.1 A/AA) + keyboard** accessibility pass over the key pages via
Playwright (`npm run test:a11y`). See [docs/](docs) for architecture, the demo
script, and the submission write-up.

## Architecture

```
Browser (semantic HTML + progressive-enhancement JS, PWA)
        │  HTTPS
Django views (server-rendered, keyboard-first, no-JS-safe)
        │
core/  ─ passport_schema.py   typed Access Passport (pydantic)
        ─ barriers.py          barrier taxonomy + deterministic detection
        ─ compiler.py          the Accessibility Compiler (source → cards)
        ─ cards.py             card builders, plain-language, contract validator
        ─ safety.py            action classification + confirmation floor
        ─ resources.py         explainable resource matcher + aggregate signal
        ─ ocr.py / ai.py       multimodal input + provider-neutral AI (local by default)
        ─ state.py             task state machine
        ─ models.py            AccessProfile, TaskSession, AccessCard, ConsentGrant, AuditEvent, Phrase
SQLite (dev) — no raw survey PII in the application layer
```

See `docs/` for `ARCHITECTURE.md`, `ACCESSIBILITY.md`, `PRIVACY.md`, and `DEMO.md`.

## Judging-criteria alignment

- **Impact** — completes real everyday tasks (medicine, forms, appointments) with
  less dependence, for many intersecting access needs.
- **Accessibility & inclusive design** — WCAG 2.2 AA, no-JS-safe, no-diagnosis,
  respectful language; the app models the accessibility it advocates.
- **Functionality** — a working end-to-end pipeline: input → barriers → compile →
  play → complete, plus communication and resources.
- **Creativity** — "accessibility as compilation" and a portable Access Passport.
- **Technical implementation** — deterministic, testable engine; typed schemas;
  policy-enforced safety; 33 automated tests; offline-capable.
- **Presentation & clarity** — transparent "Why these steps?" page exposes the
  barrier analysis, task graph, and the accessibility contract check.

## Limitations & roadmap

Deterministic barrier rules cover common patterns; an optional, schema-validated
language model can enrich them. OCR needs the Tesseract binary. The population
layer uses a small self-contained sample. Next: co-designed testing with disabled
users, on-device inference, richer document layout parsing, and localization.
