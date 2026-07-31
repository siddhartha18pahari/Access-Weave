# AccessWeave — 3-minute demo script

**Setup:** Chrome or Edge, logged in as **demo / accessweave**, light theme,
microphone + camera permissions already granted, one sample task pre-loaded.
Run `python manage.py seed_demo` beforehand.

> Rehearse once so the vision model is cached — its first load takes up to a
> minute. After that it starts instantly.

---

## 0:00 — The problem (20s)

> "People with disabilities don't face one big barrier. They face a pile of small
> ones — a label they can't read, a bill in dense language, a form that assumes a
> mouse. Every tool solves *one* of those and leaves you to stitch the rest
> together. AccessWeave asks a different question: not *what's your diagnosis*,
> but **what would make this task accessible to you** — and then actually does it."

## 0:20 — Accessibility as compilation (55s) ⭐ *the core idea*

- **New task** → click **"Use the medicine example"**.
- Hit **Make it accessible**.
- Land on **Step 1 of 6**. Advance to the dose card:
  *Take: one capsule · When: twice daily · With: food.*
- Advance again to the **warning card**:

> "Notice this. The limit is shown **exactly as it was printed**. AccessWeave
> never rewrites a safety instruction — it can reformat, but it will never
> reword a dose."

- Click **"Why these steps?"**:

> "And it's not a black box. Here are the barriers it found, the evidence for
> each, the task graph, and the accessibility checks it ran before showing me
> anything."

## 1:15 — One app, every sense (45s)

Open the **command palette** with **Ctrl+K** — type to jump between these:

- **Look around** → press Start, point the camera:
  > *"I can see a person on your left, a chair ahead."* — "Live object detection,
  > running entirely on this device. No video ever leaves it."
- **Sound Watch** → Start, then clap:
  > "For someone who can't hear the doorbell — a visual alert and a vibration.
  > And it keeps watching **when you switch tabs**, because detection runs on the
  > browser's audio thread."
- **Conversation mode** → speak toward the mic:
  > "Their words, in big live captions. I reply with a phrase and it speaks for me."

## 2:00 — Control it however you can (40s) ⭐ *the differentiator*

- Press **Alt+V** and say **"start a task"**, then speak a goal, then **"go"**.
  > "Fully voice-driven — navigate, operate any button, complete a task."
- Press **Alt+S** for **switch scanning**; press any key when the highlight lands.
  > "For someone who can't use a mouse or keyboard, a single switch drives the
  > whole app. Any key, click, or adapted controller — no drivers."
- Press **?**
  > "Voice, switch, dwell, keyboard, touch. Whichever works for you reaches
  > exactly the same place."

## 2:40 — Yours, and private (15s)

- **Passport → Show QR:**
  > "Your preferences — never a diagnosis — travel to any device by QR."
- **Privacy:**
  > "Photos and audio are read on-device. Medical actions are never automatic.
  > One click deletes everything."

## 2:55 — Close (5s)

> "AccessWeave measures independence, not engagement: did you finish a real task,
> with less effort and more confidence."

---

## Backup plan (if a device permission fails)

Never demo dead air — every path has a fallback:

| If this fails | Do this instead |
|---|---|
| Camera blocked | Use the **medicine example** button; note that camera OCR is the same pipeline. |
| Microphone blocked | Use the **command palette (Ctrl+K)** and **switch scanning (Alt+S)** — same destinations. |
| Vision model slow | Talk over it: it narrates progress aloud, and it's one-time. |
| No internet | Everything except the vision model and the web reader still works — the engine is deterministic and offline. |

## The one-sentence pitch

> "AccessWeave doesn't just tell you something is inaccessible — it **recompiles**
> it into a path you can actually complete, in whatever way you're able to
> interact."
