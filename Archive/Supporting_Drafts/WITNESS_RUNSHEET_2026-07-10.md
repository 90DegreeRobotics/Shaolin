# Chirox Hardware-Witness Run-Sheet — 2026-07-10

Close the three honestly-gated capabilities in `STATUS.md` with real,
inspectable output. This is a witness ritual, not a claim. Nothing here is
"done" until the command has run, the output was read, and the limitation was
visible. A passing test suite proves none of this.

Order is cheapest-first. Gates 1 and 2 are hold-and-measure (minutes). Gate 3
needs one small piece of wiring first — it is called out honestly below.

Prep once:

```powershell
cd C:\shaolin
.\.venv\Scripts\Activate.ps1
```

---

## Gate 1 — Wireframe noise floor (the number that says stance can track growth)

This is the missing measurement: how much do stance angles jitter on a *still*
full-body hold? That jitter is the noise floor. Growth smaller than the floor is
not real.

Protocol:
- Full body in frame, head to feet, side-on or front per the stance's view.
- Hold **horse stance** as still as you can for ~20 seconds.
- Do not narrate or adjust mid-hold — stillness is the whole point.

```powershell
python -m chirox.vision.audit --source 0 --seconds 20 --stance horse --frames 12
```

Read the output (default `Dojo/media/audit/<name>_<stamp>/`):
- `audit.json` — per-angle spread / std across the hold **is** the noise floor.
- The annotated frames — confirm the 12 joints land on your real body and that
  occluded joints are honestly flagged, not fabricated.

Pass condition: a recorded per-angle jitter number on a genuine full-body still
hold. Record that number in `STATUS.md` where it currently says "Unmeasured."
If joints wander off the body or half the frame is occluded, the run is honest
but not yet the clean floor — refit and rerun. Do not average away a bad hold.

## Gate 2 — Live voice conversation (one real spoken exchange, logged)

The ear runs and passes self-test; what is unwitnessed is a real
practitioner-voice round sealed to the Codex.

Optional first, to prove the wake loop end-to-end without your voice:

```powershell
python -m chirox.cli listen --self-test
```

Then the real witness — start the ear, speak the wake word and a question:

```powershell
python -m chirox.cli listen
```

Say aloud: **"Chirox, what day is it?"**

Pass condition: the wake word fires, Chirox answers in the Master's voice from
real day/record evidence (or refuses honestly if Ollama is down — that also
counts as truthful), and the exchange is sealed as a `conversation` record.
Confirm the seal:

```powershell
python -m chirox.cli verify
```

`verify` must still report an intact hash-chained Dojo Record after the exchange.
Record the witnessed line in `STATUS.md` (it currently says "One 'Chirox, what
day is it?' closes this.").

## Gate 3 — Fused two-camera verdict (needs a small wire first — stated plainly)

Honest truth from the code: `chirox/vision/multicam.py` has a tested `fuse()`
that combines per-camera `StanceReading`s into one `FusedReading`, and
`CameraRegistry.default_rig()` exists — but **nothing runs `fuse()` over a live
dual-camera run.** The web deck streams two cameras; it does not call `fuse()`.
So this gate is not a hold-and-measure — it is one small integration, then a
witness. Do not report it closed on the strength of the unit test alone
(`STATUS.md` already says the fused verdict "remains unexercised").

The bounded wiring (smallest honest path):
- A tiny runner (or a deck action) that opens front + side via
  `chirox/vision/capture.py`, runs `tracker` on each to a `StanceReading`, calls
  `multicam.fuse({"front": ..., "side": ...})`, and prints/streams the
  `FusedReading` with its Measured / Uncertain / No-body tags.
- Keep it to the measured two-stream ceiling (the hub collapses at three).

Then witness:
- Front + side live on a real body, one fused verdict displayed, and the truth
  tags behaving under fire (e.g. drop out of side-view frame → the fused verdict
  degrades honestly rather than inventing a reading).

Pass condition: a live dual-camera run whose *fused* verdict was displayed and
inspected, plus the honest-degradation check. Only then update `STATUS.md`.

---

## What does not count (same standard as RUN_PROOF.md)

- A passing test suite does not prove a live camera run.
- `fuse()`'s unit test does not prove a live fused verdict.
- A self-test does not replace a real spoken exchange.
- A model response does not prove body truth.

Proof means code ran, output existed, limitations were visible, and the result
was inspected. When a gate closes here, move its line in `STATUS.md` from the
"honestly gated" list to "built and verified," dated, with the witnessed number
or artifact — no earlier.
