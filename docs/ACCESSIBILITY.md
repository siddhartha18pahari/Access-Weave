# Accessibility statement

AccessWeave targets **WCAG 2.2 AA** and models the accessibility it advocates.

## Input equity

The core commitment: **whichever way you can interact, you reach the same
place.** Nothing is voice-only, and nothing is JavaScript-only.

| Method | How |
|---|---|
| **Keyboard** | Full operation, visible focus, skip link, no traps. |
| **Voice** | 🎙 button or **Alt+V** — navigate, operate any control by name, read, adjust, complete tasks. |
| **Switch** | **Alt+S** — a highlight scans the controls; any key, click, or game-controller button selects. Adapted switches need no drivers. |
| **Dwell** | **Alt+D** — rest the pointer (or a head/eye tracker); a countdown ring fills before activating. |
| **Command palette** | **Ctrl/⌘+K** — every feature in a few keystrokes. |
| **Touch** | Passport-driven target size (44–96 px). |

If the passport declares switch or dwell, the app **offers it automatically**
rather than making the user find a setting.

## Perceivable

- **Atkinson Hyperlegible** (Braille Institute), vendored locally for offline use.
- Text resize to **300%**, reflow with no horizontal scrolling, ~70ch measure,
  tuned line height and letter/word spacing.
- **Four themes** — light (default), dark, high contrast, plus reduced-motion —
  all contrast-audited, including a per-theme foreground token so destructive
  buttons stay readable everywhere.
- **No colour-only meaning**: status always carries text or an icon.
- Speech output for every card; **live captions** for incoming speech; **visual
  and haptic alerts** for sound.

## Operable

- Every action is a real form or link, so the app works with **JavaScript off**.
- **Reduced motion** honoured from both the OS setting and the passport — every
  animation, including the scanning ring and alert pulse, is disabled.
- **No strobing**: the Sound Watch alert is a single slow pulse (WCAG 2.3.1).
- **Focus mode** (Alt+F) dims rather than removes, so nothing becomes unreachable.
- Modals (partner card, palette, shortcut sheet) trap Tab and **restore focus**.
- No forced timeouts; progress survives a refresh.

## Understandable

- Plain-language pass; **one step at a time**; progress and recovery on every
  multi-step task.
- **Reduced-choice mode** trims the home screen to essentials.
- Uncertainty is shown, not hidden — confidence badges and "please verify" flags.
- **No diagnosis is ever requested.** Language avoids infantilising or
  "overcoming disability" framing.

## Robust

- Semantic landmarks, one `h1` per page, logical heading order, native controls
  with real `<label>`s.
- `aria-live="polite"` status region (deliberately not assertive for routine
  step changes); combobox pattern with `aria-activedescendant` in the palette.
- Graceful degradation everywhere: no mic, no camera, no AudioWorklet, no
  network, or no JS each produce a **clear spoken and visible explanation**, never
  a silent failure.

## Testing evidence

- [x] **48 automated tests** — compiler, safety policy, state machine, ownership,
      deletion, privacy, and URL-fetch guards
- [x] **axe-core (WCAG 2.1 A/AA)** over 15 pages in CI, failing on serious/critical
- [x] Keyboard-path test: create a task and step through it
- [x] Skip-link-is-first-focusable test
- [x] Palette combobox, shortcut sheet, and switch-scanning tests
- [x] Destructive-button contrast asserted in **all three themes**
- [x] No-JavaScript walkthrough
- [ ] NVDA / VoiceOver session with screen-reader users *(planned)*
- [ ] Co-design sessions with disabled users *(planned — the most important
      remaining item; nothing here substitutes for it)*

## Known limitations

- **Look around** needs the tab visible; browsers suspend video in background
  tabs. Sound Watch is unaffected — it runs on the audio thread.
- Camera OCR and object detection fetch their models on first use.
- Live captions and voice control need Chrome or Edge; everything else works in
  any modern browser, and the app says so rather than failing quietly.
