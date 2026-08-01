# Recording kit — read this aloud, do the actions

A teleprompter script for the 3-minute demo. **Left column = say it. Right column
= do it.** Total ≈ 2:55, leaving buffer.

## Before you hit record (5 minutes, do not skip)

| # | Step | Why |
|---|---|---|
| 1 | Open **Chrome or Edge** (not Firefox/Safari) | Voice control and live captions need the Web Speech API |
| 2 | Go to **https://accessweave.vercel.app**, log in as `demo` / `accessweave` | Demo account is pre-seeded with one clean task |
| 3 | Visit **/look/** once, press Start, allow camera, wait for the first description | ⚠️ The vision model downloads on first use (up to a minute). Do this *now* so it's cached and instant on camera |
| 4 | Visit **/soundwatch/**, press Start, allow the microphone | Gets the permission prompt out of the way |
| 5 | Close both, return to the home page | Clean starting frame |
| 6 | Set browser zoom to **100%**, window **1280×800**, hide bookmarks bar | Legible when Devpost scales the video down |
| 7 | Put something recognisable on your desk — a cup, a chair in frame, a phone | Gives "Look around" something to detect |
| 8 | Silence notifications | Nothing worse than a Slack ping mid-take |

**Recording tools (free):** OBS Studio (best), or Windows **Game Bar** (`Win+G` → record) for a quick capture. Record the **browser window**, not the full screen.

---

## The script

### 0:00 — The problem (20s)
> "People with disabilities don't face one big barrier. They face a pile of small
> ones — a label they can't read, a bill in dense language, a form that assumes a
> mouse. Every tool solves one of those and leaves you to stitch the rest together.
>
> AccessWeave asks a different question: not *what's your diagnosis*, but **what
> would make this task accessible to you** — and then it actually does it."

*On screen:* the home hub, sitting still.

---

### 0:20 — Accessibility as compilation (55s) ⭐ the core idea
> "Here's a medicine label — the kind of dense text that's genuinely hard to read."

*Do:* **Start a task** → click **"Use the medicine example"** → **Make it accessible**.

> "It didn't just tell me this was hard. It rebuilt it. Step one of six."

*Do:* click **Mark done & next**.

> "The dose, pulled out and laid out plainly. One capsule, twice daily, with food."

*Do:* click **Mark done & next** to reach the warning card.

> "And this is the part I care most about. The limit is shown **exactly as it was
> printed**. AccessWeave will reformat a medicine label — it will never reword one."

*Do:* click **Why these steps?**

> "It's also not a black box. Here are the barriers it found, the evidence for each,
> the task graph, and the accessibility checks it ran before showing me anything."

---

### 1:15 — One app, every sense (45s)
*Do:* press **Ctrl+K**, type `look`, press **Enter**. Press **Start camera**, point at your desk.

> "Point the camera and it tells you what's in front of you — with position.
> That's running entirely on this device. No video ever leaves it."

*Do:* Ctrl+K → `sound` → Enter → **Start watching** → **clap once**.

> "For someone who can't hear the doorbell: a visual alert and a vibration. And it
> keeps watching when you switch tabs, because the detection runs on the browser's
> audio thread."

*Do:* Ctrl+K → `conversation` → Enter → **Start captions** → say *"hello, can I help you?"*

> "Their words, in large live captions. I reply with a phrase and it speaks for me."

---

### 2:00 — Control it however you can (40s) ⭐ the differentiator
*Do:* press **Alt+V**, say **"start a task"**, then speak *"help me cook dinner"*, then say **"go"**.

> "Fully voice-driven. Navigate, press any button by name, complete a whole task."

*Do:* press **Alt+S**. Let the highlight step twice, then press **any key**.

> "And for someone who can't use a mouse or a keyboard, a single switch drives the
> entire app. Any key, any click, any adapted controller — no drivers needed."

*Do:* press **?**

> "Voice, switch, dwell, keyboard, touch. Whichever one works for you reaches
> exactly the same place."

---

### 2:40 — Yours, and private (15s)
*Do:* Ctrl+K → `passport` → Enter → **Show QR**.

> "Your preferences — never a diagnosis — travel to any device by QR code."

*Do:* Ctrl+K → `privacy` → Enter.

> "Photos and audio are read on your device. Medical actions are never automatic.
> One click deletes everything."

---

### 2:55 — Close (10s)
> "AccessWeave measures independence, not engagement. Did you finish a real task,
> with less effort and more confidence."

*On screen:* end on the home hub.

---

## If something fails live

Never sit in dead air — every path has a fallback:

| Fails | Say this, do this |
|---|---|
| Camera won't open | "The camera path uses the same pipeline" → use the **medicine example** instead |
| Mic/voice blocked | "Every voice command is also a button" → use **Ctrl+K** and **Alt+S** — same destinations |
| Vision model slow | Let it narrate: *"it's telling me it's preparing — that's one-time"* |
| Anything 500s | Reload once. The deterministic engine works offline; only vision and the URL reader need the network |

## After recording

- Trim dead air at both ends
- **Add captions** — a demo of an accessibility tool without captions undercuts you
- Export **1080p, under 3 minutes**
- Upload unlisted to YouTube and paste the link into Devpost

## Facts you can state accurately

- 49 backend tests + 21 automated accessibility tests, **CI passing**
- axe-core (WCAG 2.1 A/AA) runs over 15 pages on every push
- Works **keyboard-only and with JavaScript disabled**
- Vision, camera OCR, and sound detection run **on-device**
- Atkinson Hyperlegible (Braille Institute's low-vision typeface)
