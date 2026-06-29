# Roadmap
## From Manual Corpus to Deterministic Training Tool

This roadmap keeps ambition tied to proof. A phase is not complete until its output exists in the repository and can be inspected.

## Phase 0: Public Doctrine and Truth Surfaces

Status: in progress.

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

Status: planned.

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

Status: planned.

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

Status: planned.

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

Status: planned.

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

Status: planned.

Goals:

- define payload contract for Chronos
- ingest Dojo Record JSON
- summarize only from recorded facts
- preserve no-AI-form-diagnosis rule

Done when:

- Chronos-side contract exists
- sample payload passes validation
- debrief uses facts without inventing posture claims

## Phase 6: Public Reviewed Release

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
