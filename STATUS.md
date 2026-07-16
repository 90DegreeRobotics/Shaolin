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
  - `cli.py` — `chirox init | today | log | library | vision | record | timeline | review |
    debrief | sage | growth | say | listen | narrate | train | memory | forget |
    verify`. `library` lists the readable local docs/books without starting
    audio; `memory` lists what the Master can recall; `forget <seq> --reason`
    seals a recorded withdrawal so a bad exchange (e.g. a mis-transcription)
    stops feeding future conversations. The CLI is
    the developer surface; the practitioner's surfaces are the deck and the voice.
  - `web/` - a local-only mode cockpit (FastAPI on `127.0.0.1:8765`, opened as its
    own app window by the desktop **Chirox** shortcut - no address bar, its own
    browser profile). **Launch + camera legibility (2026-07-16):** the shortcut now
    opens **fullscreen** (`--start-fullscreen`; F11 to drop out), and the mirror
    shows a **"Waking the camera…" overlay** (spinner + honest text) the moment
    MIRROR starts, clearing on the first painted frame and turning into the real
    reason if the camera fails to open. The persistent Edge profile means CSS/JS
    are cache-busted by an explicit `?v=` query that MUST be bumped on every
    change (it was the reason a fresh wireframe could look unchanged on launch;
    now at `v=10`). **Training Mode** is the
    current primary practice surface: one built-in-webcam mirror, wireframe overlay,
    reference exercise guide, deterministic stance metrics, and explicit Measured /
    Uncertain / No-body truth states. **Head and neck (2026-07-16):** the cockpit
    wireframe now draws a head — an open circle riding the midpoint of the ears,
    sized from the ear span (falling back to shoulder width when the head is
    turned) — joined by a neck line to the shoulder midpoint, so the mirror shows
    a whole practitioner instead of a headless figure. Head landmarks (nose + both
    ears) are overlay-only: they never touch the deterministic stance geometry,
    which still reads its own 12-joint map. Verified 2026-07-16 by driving the
    overlay with a synthetic full-body pose: an open head ring and a continuous
    neck render above the shoulders where nothing was drawn before. **The Training Hall (2026-07-06):** the full
    24-drill catalog lives ON the page (grouped: stances/balance, legs, floor/core,
    qigong), each drill mapped by eye to its OWN chart among the practitioner's ten
    posters (real printed titles, never "Reference N"); all ten charts sit on a
    shelf and open in a fullscreen lightbox (arrow/ESC navigation) — reference
    images at human scale, not thumbnails. The webcam mirror auto-starts in
    Training Mode (skipped while the trainer or recorder holds the camera;
    ?autostart=0 disables). **WAKE (2026-07-06):** one button starts Ollama if it
    is down (spawns `ollama serve`, waits up to 15s, reports honestly if absent)
    and sets the ear listening; Ollama state is part of /api/control/status.
    **Recording made legible (2026-07-06):** the mirror is labeled "nothing is
    saved" and shows which hold it is tracking; picking ANY of the 19 holds in
    the Training Hall retargets the live wireframe (the backend always could —
    the UI had hardcoded three chips). A recording marker file makes "am I
    being recorded?" answerable: a red pulsing RECORDING banner with the
    exercise name, live elapsed time, and a STOP button; stopping keeps the
    video and honestly marks it "not sealed (stopped early)". A Recordings
    panel lists every video in `Dojo/media` (date, day, duration, size, sealed
    state, path) with PLAY in the cockpit (new recordings try H.264 so the
    browser can decode them; old mp4v files may need) OPEN in the system
    player, and OPEN FOLDER. When a recording ends the mirror comes back by
    itself. Full cycle verified live: start → banner + elapsed → STOP → file
    in the archive → mirror auto-restored. **Learning Mode** is the study surface:
    conversation with Master Chirox, Piper/Whisper activity, read-along library,
    Mandarin focus, and a day-by-day Dojo Record editor that seals new versions
    instead of silently rewriting history. The previous multi-camera control deck
    remains a measured experiment, not the default practitioner path.
- `tests/` - 234 passing unit tests as of `python -m pytest` on 2026-07-16.
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
