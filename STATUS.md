# Status
## Current Truth as of 2026-06-30

This repository is a public discipline manual **and** a working first version of
the Chirox software system.

The manual is the center. The software is real but young: its deterministic and
record-keeping organs are built and tested; its Master voice runs on a local
model; and two capabilities remain honestly gated on physical hardware.

## What Exists (built and verified)

- `README.md` establishes the public purpose of the project.
- `1yeartoShaolin.md` is the current primary manual.
- `Mandarin/` contains the Mandarin, pinyin, calligraphy, and journaling lane.
- `Diet/` is the food-as-training lane (plant-forward pragmatic, four-quarter
  arc: stabilize → cleanse → sharpen → sustain) that the Master grounds in and cites.
- `Wisdom/` is a public-domain philosophy corpus (Tao Te Ching, Analects,
  Dhammapada, Art of War) that Chirox the sage grounds in and cites — never fabricated.
- `chirox/` is the Python package that implements Chirox:
  - `calendar.py` — date → day number, phase, week, quarter, checkpoint, weekly-review.
  - `record/` — an **append-only, hash-chained Dojo Record** (Forever Law) with
    `verify()` and recorded (never silent) forgetting; the manual's daily,
    weekly, monthly, and Mandarin templates shipped as fillable files; and an
    ingest path that parses filled templates into validated entries.
  - `sentinel.py` — a fail-closed authorization gate (Sentinel Law) that seals
    every consequential write as evidence before it happens.
  - `vision/` — **deterministic** stance geometry (Ma Bu + Gong Bu) with an
    explicit UNCERTAIN gate, general range-of-motion measurement for flowing
    sequences (e.g. the Eight Brocades — measured, never graded), a session
    schema, a webcam/video runner and a **session recorder** (video archive +
    sealed manifest = the visual timeline), and a multi-camera fusion aggregator.
    Pose tracking uses the **MediaPipe Tasks API** (`PoseLandmarker`). No model
    touches form assessment.
  - `master/` — a local-Ollama Master voice (default `qwen2.5:14b-instruct`) that
    interprets **only from recorded evidence**, with in-voice discernment (the
    manual's green/red teaching) that informs but never filters. Diet/breath/
    recovery guidance is grounded in the manual and the Diet lane, quarter-aware.
    Includes a **wise-sage register** (`sage.py`): grounded philosophical dialogue
    over the wisdom corpus with a growth ledger (qualitative, not competition).
  - `wisdom.py` — the sage's RAG over the public-domain corpus (cited, never faked).
  - `voice.py` — local, sovereign speech: Piper TTS + faster-whisper STT, offline;
    TTS→STT round-trip verified at 100% on a test phrase.
  - **One identity: Master Chirox.** Internal engines (reflex, memory, brain, sage,
    voice) are never surfaced as separate voices; no runtime dependency on any
    other project.
  - `cli.py` — `chirox init | today | log | vision | record | timeline | review |
    debrief | sage | growth | say | verify`.
- `tests/` — 49 passing unit tests.
- `Dojo/witness/PROOF_2026-06-30.md` and `sample_vision_session.json` — inspected
  proof artifacts (no personal data).

## What Is Honestly Gated (not yet proven)

- **Live webcam session.** The full path — real human → 33 landmarks → Chirox
  geometry → deterministic verdict — is now verified on a real person *image*
  (2026-07-01, mean confidence 0.99). A live webcam is the same code path with a
  live source; the remaining step is the practitioner running an actual session.
- **Synchronized multi-camera capture on the physical Weatherman rig.** The fusion
  logic is built and single-source verified; the two-camera live run needs the
  hardware (two C920s into OBS) and is pending.
- **Chronos ingestion — no longer a goal.** Chirox is self-contained: its own
  append-only Dojo Record, interpretive brain, and wise-sage register. Chronos
  (`c:\chronos`) was a *pattern source* for the architecture, not a runtime
  dependency and not a voice inside Chirox. There is one identity: Master Chirox.
- **Tao Te Ching / Analects grounding.** The Master cites the manual only. Those
  public-domain texts are not present; add them under `corpus/` to widen grounding.

## Chirox Truth

Chirox is now a working local system, not only a concept:

- machine as deterministic measuring layer (no generative form diagnosis)
- append-only, tamper-evident record of the year
- a Master voice bound to recorded evidence, refusing to fabricate
- fail-closed authority on consequential writes

It is young. The physical multi-camera rig and live-camera runs are the honest
frontier. Until those are run on hardware, they are described as gated.

## Document Authority

1. `README.md`
2. `STATUS.md`
3. `SAFETY.md`
4. `1yeartoShaolin.md`
5. `Mandarin/README.md`
6. `ROADMAP.md`
7. supporting and archived drafts

## Proof Standard

Do not say a feature works until it has been run and its output inspected.

Physical-assessment features are real only when they have code, a reproducible
command, sample input or fixture, emitted output, a documented limitation, and a
test or witness artifact. Manual truth is not software truth; software truth is
not hardware truth.
