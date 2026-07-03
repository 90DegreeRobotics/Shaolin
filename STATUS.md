# Status
## Current Truth as of 2026-07-01

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
  - `listener.py` — the **always-on ear**: a wake-word daemon (`chirox listen`,
    autostart via `Launch_Chirox_Voice.ps1 -Install`). Deterministic energy-gate
    VAD (no model) segments mic audio; Whisper transcribes locally; nothing is
    acted on without the wake word "Chirox". Routes to a local day answer or the
    Master (who stays honest when Ollama is down). **Conversation register**
    (2026-07-03): any spoken question becomes a normal dialogue — the Master's
    persona over real evidence, spoken-length answers, a rolling few turns of
    context, and **every exchange sealed to the Codex** as a `conversation`
    record. First live round verified against local Ollama. Wake round-trip proven by
    `--self-test` (Piper speaks the wake phrase, Whisper hears it, routing fires);
    live mic stream + noise-floor calibration verified on the laptop 2026-07-02.
  - `narrator.py` — **long-form reading aloud** (`chirox narrate`, or by voice:
    "Chirox, read the manual"). **Read-me mode** ("Chirox, read me the tao te
    ching"): passage-by-passage in the ear itself — mic off during each passage,
    a short listening window between passages to stop, and per-book bookmarks
    (`Dojo/data/reading_progress.json`). The spoken library = repo docs plus the
    eight wisdom-corpus books, resolved fuzzily (Whisper's "dhamma pada" finds
    The Dhammapada). Markdown is cleaned to speakable prose, chunked
    at sentence/paragraph boundaries, and synthesized one chunk ahead of playback
    so any size text starts speaking in seconds — through one continuous audio
    stream (no per-chunk stop/start choppiness). **One being, one voice:** the
    narrator speaks with the Master's voice (`en_GB-alan-medium`); the second
    voice model was removed 2026-07-03. Verified 2026-07-02: manual → chunks →
    audio; Whisper round-trip reads back the opening faithfully. The ear stops a reading on "Chirox, stop" and ignores its own
    narration echo (wake-word suppression while a narration PID is live).
  - `trainer.py` — **Chirox calls the training** (`chirox train`, or by voice:
    "Chirox, train me"). He picks drills the Record shows you practice least
    (deterministic, least-practiced-first), announces each aloud, watches through
    the mirror, and speaks corrections — only the stance evaluators' own flag
    messages, rate-limited, never invented. Results are measurements ("62 percent
    in form; most frequent fault: spine slouching"), sealed as `training_call`.
    **No pose from the practitioner's body ever becomes a template** — correct
    form lives in `stances.py` as reviewable code from published standards.
    **The drill catalog is the full reference-chart set (2026-07-04): 19
    measurable holds** — horse, bow, crane, one-leg stand, drop stance, T
    stance, parallel ready, narrow meditation, empty/cat, plank, wall sit,
    squat hold, hollow hold, glute bridge, leg raise, arms raised, wuji
    standing, horse guard, seated meditation — built on a declarative
    template engine (`PoseTemplate` rules: angles, above/below, tilt,
    asymmetric legs) so every entry shares the same uncertainty gate and
    tests. **Plus 5 counted rep drills** (`vision/reps.py`): squats, pushups,
    situps, knee raises, jumping jacks — hysteresis-gated cycle counting on
    pure geometry, each rep spoken aloud as it completes. Dynamic/circular
    chart work (mobility circles, brocades, cardio drills) stays measured-not-
    graded via range-of-motion recording, per the manual's own rule.
    Verified 2026-07-03: full loop runs on hardware; with legs out of frame it
    scored nothing and said so.
  - `vision/audit.py` — **wireframe accuracy audit**: runs the tracker over a clip
    (or live grab), writes frames with the 12-joint skeleton and angles drawn on
    the real image plus `audit.json` (per-angle spread/std = the noise floor on a
    still hold). First audit 2026-07-02: joints land on the body; occluded joints
    honestly flagged, no angles fabricated.
  - **One identity: Master Chirox.** Internal engines (reflex, memory, brain, sage,
    voice) are never surfaced as separate voices; no runtime dependency on any
    other project.
  - `cli.py` — `chirox init | today | log | vision | record | timeline | review |
    debrief | sage | growth | say | listen | narrate | train | verify`. The CLI is
    the developer surface; the practitioner's surfaces are the deck and the voice.
  - `web/` — a local-only cockpit (FastAPI on `127.0.0.1:8765`, opened as its
    own app window by the desktop **Chirox** shortcut — no address bar, its own
    clean browser profile, cache-proof by three layers): live
    camera + skeleton overlay for front/side views, deterministic stance metrics,
    and explicit Measured / Uncertain / No-body truth states. As of 2026-07-03 it
    is the **full control deck** (`web/control.py`) — the practitioner never
    needs a terminal or a text field: one toggle row (MIRROR · EAR · TRAIN ·
    READ · RECORD · MASTER · SILENCE) drives everything; choices are chips, not
    typing. **Three camera boxes**, two live at a time — measured hub truth
    (2026-07-03): three simultaneous streams collapse to 0 fps even downscaled,
    two hold 22 fps, so the third box is a one-click swap. The mirror yields
    the camera automatically when training or recording starts. Verified live
    in-browser: toggles drive real processes, wireframe and corrections stream
    on a real body. All camera opens go
    through `vision/capture.py`, which requests the full 16:9 wide view (1280x720,
    hardware-verified on the rig's camera 0) instead of the cropped 640x480 default,
    and picks the backend per device: camera 1 uses DirectShow because Media
    Foundation takes ~40s to open it (measured 2026-07-03; the C920s stay on MSMF
    for 30fps). The mirror launcher releases cameras gracefully before replacing
    a running server.
- `tests/` — 180 passing unit tests.
- `Dojo/witness/PROOF_2026-06-30.md` and `sample_vision_session.json` — inspected
  proof artifacts (no personal data).

## What Is Honestly Gated (not yet proven)

- ~~Live webcam session.~~ **Closed 2026-07-03:** two cameras streamed live in the
  deck with the wireframe locked on the practitioner's real body and deterministic
  corrections displayed ("stance collapsing", "spine slouching") — witnessed
  in-browser. The front view honestly read Uncertain when only the upper body was
  framed; the side view honestly read No body. The truth states work under fire.
- ~~Synchronized multi-camera capture.~~ **Closed within hardware limits 2026-07-03:**
  front + side ran simultaneously with live pose tracking. The measured ceiling is
  two streams (three collapse to 0 fps through the hub); a fused two-camera
  *verdict* (multicam aggregation over a live dual run) remains unexercised.
- **Voice conversation on the live mic.** The ear daemon runs on hardware, the wake
  loop passes self-test, and one full conversation round is verified against local
  Ollama — but a live spoken exchange (practitioner's voice → wake → answer) has
  not been formally witnessed in a log. One "Chirox, what day is it?" closes this.
- **Wireframe noise floor.** The audit tool is built and run on archive footage
  (upper body only). Unmeasured: angle jitter on a full-body still hold — the
  number that says whether stance angles can track growth. Protocol: full body in
  frame, hold horse stance still ~20s, run the audit.
- **Chronos ingestion — no longer a goal.** Chirox is self-contained: its own
  append-only Dojo Record, interpretive brain, and wise-sage register. Chronos
  (`c:\chronos`) was a *pattern source* for the architecture, not a runtime
  dependency and not a voice inside Chirox. There is one identity: Master Chirox.
- ~~Tao Te Ching / Analects grounding.~~ **Closed 2026-07-03:** the wisdom corpus
  is downloaded and loaded — eight public-domain texts across Daoism (Tao Te
  Ching, Chuang Tzu), Confucianism (Analects, Confucius & Mencius), Buddhism
  (Dhammapada, Gospel of Buddha, Light of Asia), and strategy (Art of War) —
  7,272 passages grounding the sage, all readable aloud via read-me mode.

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
