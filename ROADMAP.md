# Roadmap
## From Manual Corpus to Deterministic Training Tool

This roadmap keeps ambition tied to proof. A phase is not complete until its output exists in the repository and can be inspected.

## Phase 0: Public Doctrine and Truth Surfaces

Status: substantially complete (2026-06-30).

Goals:

- public README
- primary one-year manual
- safety file
- status file
- roadmap
- license notice
- archived older drafts

Done when:

- front page states what exists and what does not
- Chirox is labeled as planned, not built
- older scaffold docs no longer compete with the current manual

## Phase 1: Dojo Record Templates

Status: done (2026-06-30). Templates ship in `chirox/record/templates/`; ingest
parses filled templates into validated entries; personal logs stay in git-ignored
`Dojo/data/`.

Goals:

- daily paper template
- weekly review template
- monthly checkpoint template
- Mandarin journal template
- optional CSV or Markdown log format

Done when:

- templates exist in a public folder
- a reader can start Day 1 without inventing structure
- no personal/private logs are committed

## Phase 2: Deterministic Stance Timer

Status: done (2026-06-30). Superseded by direct deterministic geometry: the
Dojo Record captures stance duration/pain/notes, and `chirox/vision/schema.py`
emits a JSON session summary with a schema test.

Goals:

- simplest possible local timer
- manual entry of stance duration, pain level, and notes
- JSON output for a single session
- no camera required

Done when:

- command runs locally
- sample JSON output exists
- test verifies schema
- README or guide shows the command

## Phase 3: MediaPipe Proof of Concept

Status: done (2026-07-03). Pose landmarks map into pure, unit-tested stance
geometry with explicit uncertainty. The live run is proven: real cameras, a real
body, the wireframe locked on, deterministic corrections displayed live.

Goals:

- camera or video-file input
- pose landmark extraction
- basic stance metrics
- explicit uncertainty and failure modes
- no generative interpretation

Done when:

- sample video or fixture can be processed
- output JSON contains measurable values
- limitations are documented
- at least one test or witness artifact exists

## Phase 4: Chirox Dojo Pipeline

Status: done within hardware limits (2026-07-03). The pipeline emits deterministic
session payloads (duration, knee/spine metrics, wobble via flags, uncertainty) and
separates measurement from interpretation. Dual-camera simultaneous capture is
hardware-verified (~22 fps each at 720p through the USB hub); three simultaneous
streams collapse to 0 fps — measured, so the deck runs two live with a swap.

Goals:

- define `dojo_vision_pipeline.py` or equivalent module
- emit deterministic session payloads
- track stance duration, knee drift estimate, spine lean estimate, heel lift, wobble count, and pain notes
- separate measurement from interpretation

Done when:

- pipeline command exists
- schema is documented
- sample outputs are committed
- false/uncertain detections are labeled clearly

## Phase 5: Chronos Ingestion

Status: superseded (2026-07-01). Chirox is self-contained — its own append-only
Dojo Record, interpretive brain, and wise-sage register. Chronos was a *pattern
source* for the architecture, not a runtime dependency. No ingestion is needed.
The remaining honest frontier is the physical multi-camera rig, not an external brain.

Goals:

- define payload contract for Chronos
- ingest Dojo Record JSON
- summarize only from recorded facts
- preserve no-AI-form-diagnosis rule

Done when:

- Chronos-side contract exists
- sample payload passes validation
- debrief uses facts without inventing posture claims

## Phase 6: The Embodied Master

Status: built and verified in stages, 2026-07-02 → 2026-07-04.

Delivered, each with tests and a witnessed run:

- always-on wake-word ear (`chirox/listener.py`) — local VAD + Whisper, honest
  when the model is down, Ctrl+Alt+0 kill switch
- one voice everywhere (Piper `en_GB-alan-medium`); long-form narration with a
  reading library (8 wisdom books + repo docs), bookmarks, read-me passage mode
- normal conversation through the Master's persona, every exchange sealed
- spoken training caller (`chirox/trainer.py`) — least-practiced drill choice,
  corrections spoken only from deterministic geometry; form templates live in
  code from published standards, never captured from the practitioner's body
- one-page control deck (`chirox/web/`) — toggle row, three camera boxes (two
  live + swap), chips not typing; launched as its own app window from a desktop
  shortcut; no terminal anywhere in the practitioner's path
- wireframe accuracy audit tool (`chirox/vision/audit.py`)

Remaining honest gates: wireframe noise-floor calibration (full-body still hold,
unmeasured) and any third simultaneous camera (hub limit, measured).

## Phase 7: Public Reviewed Release

Status: planned.

Goals:

- safety review
- docs reconciliation
- reproducible setup instructions
- known limitations
- example outputs

Done when:

- a stranger can clone the repo, read safety, run the proof, and inspect output
- the README does not overstate capability
- `STATUS.md` matches the code

## Standing Rule

If a phase is not wired, run, and inspected, it is not done.
