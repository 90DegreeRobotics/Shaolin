# Status
## Current Truth as of 2026-07-16

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
- `Docs/` contains supplementary study material. `Docs/SHAOLIN_KUNG_FU_STUDY_GUIDE.md`
  is the integrated Kung Fu study-guide lane: 18 external basics, Wu Bu Quan,
  Luohan/Qi Gong balance, staff work, digital-resource discipline, Chirox
  measurement mapping, and current outdoor-practice rule links for Normal and
  Bloomington.
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
  - `master/` — a local-Ollama Master voice that interprets **only from recorded
    evidence**, with in-voice discernment (the manual's green/red teaching) that
    informs but never filters. Diet/breath/recovery guidance is grounded in the
    manual, the Diet lane, the Training Hall, the Temple Day, Mandarin lane,
    and the Kung Fu study guide, quarter-aware. Includes a **wise-sage register**
    (`sage.py`): grounded philosophical dialogue over the wisdom corpus with a
    growth ledger (qualitative, not competition). **Persona recast 2026-07-04**
    in the register of a living Shaolin teacher: calm, measured, unhurried; one
    exact question turned inward; image → principle → practice; the five
    hindrances and recognize/accept/investigate/non-identify as working method;
    an explicit NO-THEATRE clause and a quoting rule — only words that stand
    verbatim in provided passages may be cited (one real wisdom passage is
    retrieved per spoken question so citation is grounded, not forbidden).
    **The Master remembers (2026-07-04):** sealed `conversation` events are
    recalled into every exchange — the recent turns for continuity plus older
    exchanges that share vocabulary with the question — and `forget` events are
    honored (a withdrawn exchange never resurfaces). A spoken **reflect
    register** ("Chirox, reflect" / "look back") widens the evidence windows
    (14 days, more conversations, the wisdom growth trail) and asks the Master
    to name movement, stalls, and one unseen pattern from the record only.
    Ollama calls pin `num_ctx` 8192 (no silent truncation of the persona) and
    `keep_alive` 30m (no model reload after each silence).
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
    record. **Streaming mouth (2026-07-04):** the reply is streamed from Ollama
    and spoken sentence by sentence — first words in ~10–17s warm on this
    CPU-only laptop instead of ~70s+ for the whole reply (measured live); the
    mic stays paused for the full reply and whatever was actually said is
    sealed, even if the stream dies mid-thought. Replies use a measured Piper
    pace (`speech_pace` 1.1) and Whisper segments that Whisper itself marks as
    probable non-speech are dropped (no more phantom commands from room noise).
    Voice/model choices live in config (`piper_voice`, `whisper_model`,
    `speech_pace`). Wake round-trip proven by
    `--self-test` (Piper speaks the wake phrase, Whisper hears it, routing fires);
    live mic stream + noise-floor calibration verified on the laptop 2026-07-02.
  - `narrator.py` — **long-form reading aloud** (`chirox narrate`, or by voice:
    "Chirox, read the manual"). **Read-me mode** ("Chirox, read me the tao te
    ching"): passage-by-passage in the ear itself — mic off during each passage,
    a short listening window between passages to stop, and per-book bookmarks
    (`Dojo/data/reading_progress.json`). The spoken library = repo docs plus the
    eight wisdom-corpus books, resolved fuzzily (Whisper's "dhamma pada" finds
    The Dhammapada). The local spoken-doc shelf also includes the integrated Kung
    Fu study guide. Markdown is cleaned to speakable prose, chunked
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
    **The drill catalog is the full reference-chart set (2026-07-18): 30+
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
  - `cli.py` — `chirox init | today | log | library | vision | record | timeline | review |
    debrief | sage | growth | say | listen | narrate | train | memory | forget |
    verify`. `library` lists the readable local docs/books without starting
    audio; `memory` lists what the Master can recall; `forget <seq> --reason`
    seals a recorded withdrawal so a bad exchange (e.g. a mis-transcription)
    stops feeding future conversations. The CLI is
    the developer surface; the practitioner's surfaces are the deck and the voice.
  - `web/` - a local-only mode cockpit (FastAPI on `127.0.0.1:8765`, opened as its
    own app window by the desktop **Chirox** shortcut - no address bar, its own
    browser profile). **Launch + camera legibility (2026-07-16):** the shortcut
    opens **maximized** (`--start-maximized`) so the window keeps its minimize /
    close bar, and the mirror shows a **"Waking the camera…" overlay** (spinner +
    honest text) until the first painted frame (or the real failure reason). CSS/JS
    are cache-busted by `?v=` (now at `v=11`). **Wireguy Practice Stage (2026-07-16):**
    Training Mode is a mirror-first composition — Wireguy (full-body wireframe
    including head and neck) owns the stage with an on-canvas HUD (Measured /
    Uncertain / No-body, hold timer, in-form seconds, key angles). The top bar
    keeps only mode tabs plus **WAKE** / **SILENCE**; practice actions are
    **CALL ME**, **RECORD**, and **PICK WORK** (Training Hall, ten charts, and
    recordings live in a drawer, not a permanent control deck). One drill catalog
    drives Hall, CALL ME, and RECORD. Browser playback can prepare an H.264 proxy
    or fall back to MJPEG streaming without altering evidence files. **Head and
    neck (2026-07-16):** head circle from ear midpoint + neck to shoulders —
    overlay-only, never part of stance geometry. **Head yaw + pitch (2026-07-17):**
    Wireguy reads side-to-side (yaw) and up/down (pitch) from nose vs ear line,
    with arrows and a degree readout — still overlay-only. **Full-body Wireguy overlay
    (2026-07-16):** hands (wrists + knuckles) and feet (ankles + heels + toes)
    draw on the mirror for presence; stance geometry still uses the 12-joint
    map. **Forever Routine Tracker (2026-07-16):** hybrid recognition — you name
    the sequence (PICK WORK → Named Routines, or voice *"eight brocades"*),
    Wireguy runs a phase state machine for Shaolin Temple Europe Ba Duan Jin
    (`eight_brocades_ste` in `vision/sequences.py`), counts holds/reps/heel
    clicks with UNCERTAIN pause, and **END & SEAL** writes a forever
    `routine_session` Codex entry (`totals.phases` + `phase_log`). Form quality
    is not graded from video; YouTube is teacher reference only. Voice also
    understands *"next phase"* / *"end routine"*. Free-train still tags
    `free_training` until a named routine is active. **Trainer voice (2026-07-16):**
    geometry corrections stay deterministic; sparse honest encouragement lines
    speak only on clean in-form streaks, with randomized callout gaps; auto-chosen
    drill sets keep neglect weighting and shuffle order. **Learning Mode** is the
    study surface (Master chat, Piper/Whisper, library, Mandarin, Dojo Record) with
    no training chrome. Multicam remains a measured experiment, not the default path.
    **Live recording (2026-07-17):** RECORD tees frames from the live Wireguy
    session — the mirror does not freeze or yield the camera to a headless
    CLI process. You see yourself and the wireframe while the archive writes;
    natural completion seals the manifest, STOP keeps the video unsealed.
    **Voice recording + auto-ear (2026-07-17):** the cockpit auto-wakes the ear
    (and Ollama) on launch so Chirox listens without a manual WAKE; speak
    *"Chirox, start recording"*, *"record one-legged stance for one minute"*,
    or *"stop recording"* — he answers aloud and drives the live-tee recorder.
    **One-viewport Training Mode (2026-07-18):** all practice buttons sit in the
    top bar; CALL ME / RECORD panels fly over the mirror; nothing sits below the
    camera; the stage fills the remaining viewport with no page scroll.
    **Auto-detect on open (2026-07-18):** Training Mode starts in `auto` — Wireguy
    watches first and names a known hold when geometry is clear; it does not invent
    a stance. **AUTO** returns to detect; Pick Work / CALL ME locks a hold.
    **Reference-chart detect pipeline (2026-07-18):** all ten poster PNGs map to
    drills; every hold in `HOLD_CATALOG` has geometry + chart number; auto-detect
    scores only catalog keys (no `ma_bu` aliases), prefers specific holds, and
    surfaces chart title in the HUD. New measurable holds from the posters include
    rest stance, half/deep squat, cossack, side plank, standing tree, Superman.
    **Reproduction verifier (2026-07-18):** `vision/verify.py` scores every frame
    against chart holds (0–100, IN/OUT band, spoken corrections). AUTO picks the
    closest target even when the shape is ugly — no silence until pretty. Sessions
    seal as `match_session` into the Dojo Record (mirror off or voice
    *"seal the match"*). Voice: *"how close am I?"* / *"check my form"*.
    CSS/JS cache bust is `?v=20`.
- **Voice pipeline hardening (2026-07-16):** Piper download uses timeout +
    atomic write and refuses truncated files; `Voice.preflight()` reports honest
    mouth/ear readiness before the ear greets; the mic queue is bounded (drop-
    oldest under STT backlog) with PortAudio status noted; energy VAD slowly
    refreshes its noise floor while idle; narration/training PID lock is claimed
    in the parent at spawn (closes echo wake race); cockpit SILENCE and
    `Launch_Chirox_Voice.ps1 -Stop` also kill narrator/trainer organs; self-test
    reports both prompted and live-path (unprompted) STT wake results. Gate 2
    (live mic witness) remains open.
- `tests/` - 275 passing unit tests as of `python -m pytest tests` on 2026-07-18.
- `CONTRIBUTING.md`, `SECURITY.md`, `PRIVACY.md`, `TRUTH_AUDIT.md`,
  `CURRICULUM_MAP.md`, and `HARDWARE_WITNESS_PROTOCOL.md` now define the
  public contribution, privacy, proof, curriculum, and hardware witness rules.
- `Dojo/witness/PROOF_2026-06-30.md` and `sample_vision_session.json` — inspected
  proof artifacts (no personal data).

## What Is Honestly Gated (not yet proven)

- ~~Live webcam session.~~ **Closed 2026-07-03; simplified 2026-07-04:** the live
  wireframe mirror is proven on real hardware. The current primary UI intentionally
  uses only the built-in webcam (source 0) to keep practice simple and reliable.
  External front/side/extra cameras remain possible backend experiments, not the
  practitioner-facing default.
- ~~Synchronized multi-camera primary cockpit.~~ **Retired 2026-07-04:** front + side
  did run simultaneously, but the rig workflow created more confusion than value at
  this stage. Multicam fusion returns only after calibration makes it earn its place.
- **Voice conversation on the live mic.** The ear daemon runs on hardware, the wake
  loop passes self-test, and one full conversation round is verified against local
  Ollama. **Hardened + witnessed 2026-07-16:** the `--once` proof path now holds
  until Chirox is actually addressed and answers (stray room noise no longer ends
  the run early), and every exchange is captured to an inspectable witness log
  (`Dojo/witness/live_exchange_<stamp>.local.md`, git-ignored). The no-mic
  self-test now proves the **whole chain including the day answer** — Piper spoke
  "Chirox, what day is it today?", Whisper transcribed it verbatim, it routed to
  `day`, and "Day 18 of 365 — Phase 1" rendered: PASS, witness written and
  inspected on the build laptop. The one remaining step is the practitioner's own
  live utterance into the microphone — `python -m chirox.cli listen --once`,
  "Chirox, what day is it?" — which now writes that same witness artifact. Until
  that mic run, the gate stays open.
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
