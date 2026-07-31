# AccessWeave — Architecture

AccessWeave is a privacy-first Django web app. Its central idea is
**accessibility as compilation**: an inaccessible task is parsed, its barriers are
detected, and it is *recompiled* into a validated sequence of accessible "Access
Cards" rendered in the user's preferred format. A deterministic engine does the
work, so it runs offline with no paid API; optional services (ElevenLabs voice,
a language model, OCR) enhance it but are never required.

## The Access Loop

```mermaid
flowchart LR
  A[INTENT<br/>speak / type a goal] --> B[SENSE<br/>text · photo · form]
  B --> C[UNDERSTAND<br/>barrier analysis]
  C --> D[ADAPT<br/>compile Access Cards]
  D --> E[ACT WITH CONSENT<br/>confirm consequential steps]
  E --> F[LEARN<br/>feedback tunes preferences]
  F -. updates .-> A
```

## System overview

```mermaid
flowchart TB
  subgraph Client["Browser — PWA, keyboard-first, works with no JS"]
    UI["Semantic HTML + design tokens<br/>(Access Passport → CSS vars)"]
    V["Global Voice Assistant<br/>(navigate · operate any control · read)"]
    TTS["Unified TTS<br/>ElevenLabs → browser fallback"]
    CAM["On-device camera OCR<br/>(image never uploaded)"]
    SW["Service worker + offline shell"]
  end

  subgraph Server["Django"]
    VIEWS["Views (server-rendered, ownership-checked)"]
    TTSP["/api/tts/ proxy (key stays server-side)"]
    subgraph Engine["Deterministic engine (core/)"]
      PASS["passport_schema.py<br/>typed prefs, no diagnosis"]
      BAR["barriers.py<br/>closed taxonomy + rules"]
      COMP["compiler.py<br/>source → task graph → cards"]
      CARDS["cards.py<br/>build · plain-language · validate"]
      SAFE["safety.py<br/>action class + confirm floor"]
      RES["resources.py<br/>explainable matcher"]
      STATE["state.py<br/>task state machine"]
    end
    DB[("SQLite<br/>profiles · tasks · cards · audit")]
  end

  UI --> VIEWS
  V --> VIEWS
  V --> CAM
  TTS --> TTSP
  VIEWS --> Engine
  Engine --> DB
  VIEWS --> DB
```

## Compile pipeline

```mermaid
flowchart LR
  IN["Goal + source<br/>(text / OCR)"] --> CLS{classify}
  CLS -->|medicine| MED[dose card + verbatim warning]
  CLS -->|bill| BILL[amount/due + 'never pays for you']
  CLS -->|appointment| APPT[date/place + prep + phrases]
  CLS -->|form| FORM[per-field wizard + confirm submit]
  CLS -->|instructions| INS[segment into steps]
  CLS -->|goal only| TMPL[goal templates]
  MED & BILL & APPT & FORM & INS & TMPL --> VAL["Accessibility contract<br/>validator"]
  VAL --> OUT["Ordered Access Cards<br/>+ recovery + completion"]
```

## Key design decisions

| Decision | Why |
|---|---|
| **Deterministic engine, AI optional** | Runs offline, is testable and explainable; never blocks on a paid API. |
| **Preferences, not diagnosis** | The passport stores *how software should behave*, protecting privacy and dignity. |
| **Server-rendered + progressive enhancement** | Every action is a real form/link; JS (voice, speech, OCR) only enhances — nothing is JS-only or voice-only. |
| **Design tokens driven by the passport** | One set of templates renders in each user's format (text size, contrast, motion) — no duplicated pages. |
| **Confirmation *floor* in `safety.py`** | A passport can make confirmations stricter but never weaker; medical actions are always blocked from automation. |
| **On-device OCR / server-side TTS proxy** | The photo never leaves the device; the ElevenLabs key never reaches the browser. |

## Data model (core/models.py)

```mermaid
erDiagram
  User ||--o{ AccessProfile : owns
  User ||--o{ TaskSession : owns
  User ||--o{ ConsentGrant : grants
  User ||--o{ AuditEvent : logs
  User ||--o{ Phrase : saves
  TaskSession ||--o{ AccessCard : contains
  AccessProfile ||..o{ TaskSession : "active profile"
```

- **AccessProfile** — the Access Passport (functional preferences JSON).
- **TaskSession** — one task; holds the source (erased on completion when asked),
  the analysis, the task graph, and the current step.
- **AccessCard** — one compiled, validated interface object.
- **ConsentGrant** — scoped, expiring supporter permission (never full-account).
- **AuditEvent** — minimal record that a consequential action happened (no content).
- **Phrase** — saved Communication Bridge quick messages.
