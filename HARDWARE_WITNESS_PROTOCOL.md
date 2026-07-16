# Hardware Witness Protocol
## Closing The Remaining Gates

This protocol defines the runs that turn Chirox hardware claims from "built" or
"previously witnessed" into current evidence.

Do not mark a gate closed unless the command ran, the output was inspected, and
the limitation was written down.

## Gate 1: Full-Body Wireframe Noise Floor

Purpose: measure camera/joint-angle jitter while the body is intentionally
still.

Setup:

- full body in frame
- light from the front
- feet visible
- no mirror or OBS using the camera
- shallow Horse stance or neutral full-body still hold

Command:

```powershell
python -m chirox.vision.audit --source 0 --seconds 25 --stance horse
```

Pass evidence:

- audit folder exists
- frame images show the wireframe on the real body
- `audit.json` exists
- angle spread/std are small enough to trust trend comparisons
- occluded joints are flagged instead of fabricated

## Gate 2: Live Spoken Exchange

Purpose: prove live mic to wake word to spoken answer.

Command:

```powershell
python -m chirox.cli listen --once
```

`--once` holds until Chirox is actually addressed and answers, then exits — stray
room noise no longer ends the run early. It writes an inspectable witness log to
`Dojo/witness/live_exchange_<stamp>.local.md` (git-ignored: it carries the
practitioner's own words). `listen --witness` does the same for a normal session.

Speak:

```text
Chirox, what day is it?
```

Pass evidence:

- the witness log exists and its Verdict reads `PASS`
- the logged transcript includes the wake command or an accepted wake alias
- Chirox prints or speaks the day answer (also captured in the log)
- if the model is unavailable, the log records the honest silence, not a fabrication

Before the mic run, the same chain minus the microphone can be proven end to end:

```powershell
python -m chirox.cli listen --self-test --witness
```

This has Chirox speak the phrase with his own mouth, hears it back through
Whisper, routes it, and renders the day answer — verified `PASS` on the build
laptop 2026-07-16. It leaves a self-test witness log; only the live mic run
closes the gate.

## Gate 3: Fused Dual-Camera Verdict

Purpose: prove front plus side readings can be combined without pretending more
than the cameras saw.

Suggested path:

1. Open the cockpit.
2. Start front plus side.
3. Stand full-body in frame.
4. Hold a simple stance.
5. Inspect the live state and any fused payload.

Pass evidence:

- front camera contributes the visible frontal measurements
- side camera contributes side limitations or side measurements
- missing views are named as limitations
- no pass/fail is given when required views are absent or uncertain

## Gate 4: Laptop Handoff

Purpose: prove another machine can run the public path.

Required first:

- desktop tree has a coherent commit
- remote has that commit, or the laptop receives an explicit archive
- `origin/main` divergence is resolved

Laptop commands:

```powershell
git pull
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest
python -m chirox.cli library
python -m chirox.cli verify
```

Laptop is ready only when those commands are run or the remaining blocker is
named plainly.

