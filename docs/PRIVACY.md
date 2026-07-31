# Privacy & safety

Privacy by design: the system minimizes data collection at every stage.

## Defaults
- No diagnosis is required — the passport stores functional **preferences**.
- Uploaded images are processed **in memory and discarded** (`STORE_UPLOADS=0`).
- Location is off by default; supporter access is opt-in and expiring.
- No-storage task mode erases the source the moment the task is compiled.
- No raw survey PII lives in the application layer.

## Safety boundaries (enforced, not just documented)
- Medical actions are **blocked** from autonomous execution — a policy *floor* in
  `core/safety.py` that a passport can strengthen but never weaken.
- Dosages/warnings are routed to **verbatim** warning cards and never altered.
- Machine-read content below a confidence threshold is **flagged for verification**.
- Consequential actions (submit, pay, share) require explicit confirmation, checked
  by the deterministic accessibility-contract validator before cards are shown.
- Content from files/pages is treated as **data, not instructions** (injection guard).

## Data classes & retention
| Class | Example | Default retention |
|---|---|---|
| Ephemeral input | uploaded image | deleted after processing |
| Preference | text scale, contrast | until changed/deleted |
| Task state | current step | until completion or deletion |
| Audit event | "a task was created" | minimal metadata, no content |
| Aggregate evidence | category-level rates | de-identified, no raw records |

## User controls
Delete a task (and its source) from the player, or delete **all** task data from
the Privacy page. Export your passport as a PDF (preferences only — no tokens).
