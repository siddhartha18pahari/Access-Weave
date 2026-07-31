# AccessWeave — Submission

**The adaptive independence copilot — turn any inaccessible task into a
personalized, accessible path to completion.**

Built for the **Assistive Innovation Challenge 2026**.

---

## Inspiration

People with disabilities rarely face one big barrier. They face an accumulation
of small ones: a medicine label that can't be read, a bill in dense language, a
form that assumes a mouse, an appointment letter with no plain summary. Existing
tools each solve *one* modality — a screen reader reads, OCR extracts, a
captioner transcribes — and leave the disabled person to stitch them together.
The coordinating work still lands on them.

We wanted to ask a different question. Not *"what is your diagnosis?"* but
**"what would make this task accessible to *you*?"** — and then actually do it,
end to end, in whatever way that person is able to interact.

## What it does

AccessWeave treats accessibility as **compilation**. You give it a goal and
whatever you're stuck on — by **voice**, **camera**, **URL**, or text — and it:

1. **Finds the barriers** — dense language, small print, unclear steps,
   safety-sensitive numbers, sensitive data — with evidence and confidence.
2. **Recompiles the task** into validated **Access Cards**, one step at a time,
   in *your* format: large text, speech, plain language, high contrast.
3. **Keeps you in control** — consequential actions (submit, pay, share) always
   need confirmation, and medical actions are never automatic.

It recognises **medicine labels, bills, appointment letters, forms, web pages,
and free instructions**, and covers the whole day rather than one modality:

- **Look around** — point the camera, hear what's in front of you with position.
- **Sound Watch** — a doorbell or alarm becomes a visual alert, a vibration, and
  a system notification, **even while you're in another tab**.
- **Conversation Mode** — their speech becomes big live captions; you reply with
  phrases spoken aloud.
- **Routines** — save a repeatable task and re-run it.
- **Portable Passport QR** — your preferences travel to any device.

**And you can drive all of it however you're able:** full voice control, single
**switch scanning**, **dwell** selection for head/eye trackers, a **command
palette** (Ctrl+K), keyboard, or touch. Every route reaches the same place.

## How we built it

- **Django**, server-rendered, so every page works **keyboard-only and with no
  JavaScript**. JS (voice, camera, captions, offline) is pure enhancement.
- A **deterministic accessibility engine** (`core/`): a typed Access Passport
  (pydantic), a closed barrier taxonomy, the compiler, a plain-language pass, a
  safety policy with a confirmation *floor*, an explainable resource matcher, and
  a task state machine. It runs **offline with no paid API**.
- An **accessibility-contract validator** checks every compiled card sequence
  (names, text equivalents, confirmed actions, marked uncertainty, recovery)
  before it reaches the user — and now warns the user if a check fails.
- **On-device AI**: object detection (TensorFlow.js COCO-SSD) and camera OCR
  (Tesseract.js) run in the browser — the image never leaves the device.
- **Audio-thread detection**: Sound Watch runs in an **AudioWorklet**, which
  browsers don't throttle, so it survives backgrounded tabs.
- **Optional ElevenLabs TTS**, proxied server-side so the key never reaches the
  browser, with the browser voice as an always-available fallback.
- **Atkinson Hyperlegible** (the Braille Institute's low-vision typeface),
  vendored locally; the whole UI is themed by CSS design tokens driven by the
  passport.
- **48 automated tests** plus an axe-core + keyboard CI pass, and Docker deploy.

## Challenges we ran into

- **Voice reliability** — buffering speech so long cards don't cut off,
  auto-restarting recognition, and persisting voice state across page loads.
- **Backgrounding.** Sound Watch first used `requestAnimationFrame`, which
  browsers *pause* for hidden tabs — so it silently stopped the moment you
  switched away, defeating its entire purpose. Moving detection into an
  AudioWorklet fixed it.
- **Not breaking the keyboard while adding switch input.** Our switch handler
  intercepted its own synthetic click and re-entered, so controls never fired.
- **Safety-sensitive content.** Dosages and limits are shown verbatim and never
  altered; a regex bug that silently dropped the limit card for "Maximum 4
  capsules" phrasing was caught by an adversarial review and regression-tested.
- **Polish that doesn't cost accessibility** — every animation is disabled under
  reduced-motion, and every theme was contrast-checked (we found white-on-pink
  delete buttons at 2.5:1 in dark mode and fixed them with a per-theme token).

## Accomplishments we're proud of

- A genuinely **end-to-end** pipeline: input → barriers → compile → play → done.
- **Input equity.** Voice, switch, dwell, keyboard, palette, and touch all reach
  the same destinations. The passport offered switch/dwell from day one; we made
  the app actually honour it.
- **Genuinely accessible itself** — WCAG 2.2 AA target, no-JS-safe, no-diagnosis,
  respectful language. The app models the accessibility it advocates.
- **Transparency** — a "Why these steps?" view exposes the barrier analysis, task
  graph, and contract check. No black box.
- **Safety by construction** — a policy floor a passport can't weaken;
  *"never makes a payment for you"* and *"never changes a dose"* enforced in code
  and covered by tests.
- **Privacy that's architectural, not promised** — camera frames, audio, and OCR
  never leave the device; the TTS key never reaches the browser.

## What we learned

- Accessibility isn't a feature you add; it shapes every decision.
- In voice and switch UX, **reliability beats novelty** — fallbacks, buffering,
  and re-entrancy guards matter more than a flashy demo.
- Determinism makes AI-adjacent products **testable and explainable**, which
  matters more than raw capability for assistive tools.
- An adversarial review pass found 14 real defects — including a safety-critical
  one — that ordinary testing missed.

## What's next

- Co-designed testing **with disabled users**, and prioritising their feedback
  over our assumptions.
- Group/row scanning for faster switch access on dense pages.
- On-device inference for language, and richer document-layout parsing.
- Localization: message catalogs, RTL, regional OCR and speech.

## Honest limitations

- It's a **web app**, so it cannot control your operating system, other
  applications, or run when the tab is closed. A background OS assistant would
  need a native build.
- **Look around** needs the tab visible (browsers suspend video in background
  tabs); Sound Watch does not.
- Camera OCR and object detection need internet **once** to fetch their models.
- Barrier rules cover common patterns; an optional, schema-validated language
  model can enrich them, but the deterministic engine is always the floor.

## Judging-criteria alignment

- **Impact** — completes real everyday tasks with less dependence, across
  vision, hearing, motor, cognitive, and communication needs.
- **Accessibility & inclusive design** — WCAG 2.2 AA, no-JS-safe, no-diagnosis,
  five input methods, Atkinson Hyperlegible, contrast-audited themes.
- **Functionality** — a complete working pipeline plus vision, sound, captions,
  communication, resources, and routines.
- **Creativity** — "accessibility as compilation", the portable Access Passport,
  and input equity across voice/switch/dwell.
- **Technical implementation** — deterministic testable engine, typed schemas,
  policy-enforced safety, AudioWorklet backgrounding, on-device ML, SSRF-guarded
  fetching, 48 tests, CI, Docker.
- **Presentation & clarity** — the transparent analysis view, this documentation,
  and an architecture diagram in `ARCHITECTURE.md`.

## Run it

```bash
cd accessweave
pip install -r requirements.txt      # only Django + pydantic are required
python manage.py migrate
python manage.py seed_demo           # demo account + a sample task
python manage.py runserver
```

Open http://127.0.0.1:8000 and log in with **demo / accessweave**.
Optional: set `ELEVENLABS_API_KEY` for natural voice. Or `docker compose up --build`.
See [DEMO.md](DEMO.md) for the 3-minute demo script.
