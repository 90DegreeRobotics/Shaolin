# Truth Audit
## What Is Proven, What Is Measured, What Is Only Recorded

Last updated: 2026-07-16

This file is the repo's anti-hype ledger. It exists so a reader can tell the
difference between doctrine, curriculum, verified software, hardware witness,
and future work.

## Proven In Repo

| Surface | Current truth | Evidence |
| --- | --- | --- |
| Manual corpus | The one-year manual, Training Hall, Temple Day, Diet, Mandarin, Wisdom, and Kung Fu study guide exist as public text. | Files in repo. |
| Safety boundary | The repo states no medical advice, no lineage claim, no AI form authority, and the pain rule. | `SAFETY.md`, `README.md`, `1yeartoShaolin.md`. |
| Chirox package | Local Python package exists with CLI, curriculum retrieval, record, vision, voice, listener, narrator, trainer, web deck, and tests. | `chirox/`, `tests/`. |
| Unit tests | Current local run passed. | `python -m pytest` -> 226 passed on 2026-07-16. |
| Spoken library index | Chirox can list readable documents and public-domain books. | `python -m chirox.cli library`. |
| Append-only Dojo Record | Codex hash-chain implementation and tests exist. | `chirox/record/`, `tests/test_codex.py`. |

## Proven On Hardware Earlier

| Surface | Current truth | Evidence |
| --- | --- | --- |
| Live mirror | Previously witnessed with two cameras and real-body wireframe. | `STATUS.md`, witness notes. |
| Two-camera ceiling | Two streams worked; three simultaneous streams collapsed through the measured hub. | `STATUS.md`, web/control notes. |
| Wake-word self-test | TTS to STT to wake routing has a self-test path. | `chirox listener --self-test`, tests. |

## Still Gated

| Gate | Needed proof |
| --- | --- |
| Full-body wireframe noise floor | Run still full-body hold, save audit JSON/images, inspect angle spread. |
| Live spoken exchange witness | Record one live "Chirox, what day is it?" or equivalent mic exchange and note output. |
| Fused dual-camera verdict | Run front plus side, inspect fused payload and limitations. |
| Clean laptop handoff | Sync a clean, tested commit to remote or otherwise transfer a verified tree, then pull/run proof on the laptop. |

## Measurable By Chirox

Chirox may give limited deterministic feedback for static holds and counted reps
defined in code:

- stance holds in `chirox/vision/stances.py`
- counted reps in `chirox/vision/reps.py`
- training-call summaries in `chirox/trainer.py`

If visibility is low, the correct state is `UNCERTAIN`.

## Recordable, Not Graded

These may be filmed, logged, and measured for general range of motion:

- Eight Brocades
- Wu Bu Quan
- staff basics and staff forms
- kicks
- sweeps
- flowing forms
- free training

Only a human teacher or the practitioner's reviewed video can judge whether the
form is right.

## Deferred

These should remain deferred until the base is safe and a human review path
exists:

- aerial kicks
- deep sweeps
- impact conditioning escalation
- iron body claims
- weapon forms performed fast
- any remote sync or cloud sharing of private practice data

## Audit Rule

When a claim changes, update the matching truth surface in the same pass:

- `README.md` for the public front door
- `STATUS.md` for current state
- `RUN_PROOF.md` for reproducibility
- this file for proven/measured/gated classification
- tests or witness artifacts for evidence
