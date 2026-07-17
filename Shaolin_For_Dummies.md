# Shaolin for Dummies
### How to actually train with this system, starting today

This is the plain-language walkthrough. The manual (`1yeartoShaolin.md`) tells
you *why*; this tells you *which buttons to press and in what order*. Every
command here is real and tested — nothing is aspirational.

The system is four honest machines:

| Machine | What it does | What it will never do |
|---|---|---|
| **The Mirror** (Wireframe Guy) | Measures your body's angles, deterministically | Guess when it can't see you |
| **The Record** | Keeps every session forever, tamper-evident | Forget, or let you quietly edit the past |
| **The Master** | Speaks about YOUR recorded evidence (local AI) | Fabricate — if his model is down, he says so |
| **The Ear** | Always-on voice: say "Chirox…" and he answers | Send audio anywhere — everything stays on this laptop |

**You never need a terminal.** Double-click the **Chirox** icon on your desktop:
Chirox opens as its own app window (no browser tabs, no address bar) and starts
in **Training Mode**. The first screen is the built-in-webcam mirror: one live
camera, one wireframe guy, clear Measured / Uncertain / No-body truth states.

The top mode switch matters:

- **Training Mode** = mirror, exercise reference, live geometry, training controls.
  Use **PICK WORK → Named Routines** (or say *"Eight Brocades"*) so Wireguy
  counts each phase forever into the Dojo Record when you **END & SEAL**.
- **Learning Mode** = Master chat, Piper/Whisper activity, read-along library,
  Mandarin focus, and day-by-day Dojo Record fields you can edit and save.

The `chirox` commands shown below are the equivalent for anyone who *wants* a
terminal; the desktop app and voice phrases are the normal path.

```powershell
cd C:\Shaolin
.\.venv\Scripts\python.exe -m chirox.cli <command>
```

---

## Part 1 — One-time setup (15 minutes)

### 1. Establish yourself

```powershell
chirox init --start 2026-07-01     # the date your year began; day 1
chirox today                        # confirms your day number and today's focus
```

### 2. Set up the room

Your current reliable rig:

- **Camera 0 = the built-in webcam mirror.** This is the primary Training Mode
  view. External front/side/extra cameras are future calibrated-rig work, not the
  default daily practice surface.
- **Stand far enough back for the whole body.** The Mirror needs head to feet.
  If your feet are cut off, every stance number is worthless and the system
  will say `UNCERTAIN` instead of pretending. This is the #1 beginner mistake.
- Light the room from the front, not behind you (a window behind you blinds it).

### 3. Turn on the Ear (voice, always-on)

```powershell
.\Launch_Chirox_Voice.ps1 -Install    # starts now AND on every Windows boot
```

Then just talk, from anywhere in the room:

- **"Chirox, what day is it?"** → your day number and phase (works offline, always)
- **"Chirox, how deep should my horse stance be?"** → the Master answers from
  the manual and your record (needs Ollama running: `ollama serve`)
- **"Chirox, training mode."** → the app returns to the mirror surface
- **"Chirox, learning mode."** → the app switches to study mode
- **"Chirox, go to sleep."** → he stops listening (or `.\Launch_Chirox_Voice.ps1 -Stop`)

Say the name and the command together. A bare "Chirox" is not treated as an open
microphone anymore, because random room audio was waking him at the wrong times.
He pauses his ears while he talks, so he won't answer himself. If the Master's
model is off, he'll tell you honestly instead of making something up.

**You can also just talk to him.** Any question after the wake word becomes a
real conversation — "Chirox, why does my knee ache after horse stance?" — he
answers in his own voice, grounded in your record and the manual, remembers
the last few turns of the sitting, and seals every exchange into the record.

**He can also read to you, audiobook style** (same voice — Chirox has one):

- **"Chirox, read the manual."** → reads `1yeartoShaolin.md` aloud
- **"Chirox, read the guide."** → reads this document
- **"Chirox, read the Kung Fu study guide."** → reads
  `Docs/SHAOLIN_KUNG_FU_STUDY_GUIDE.md`
- Also readable by voice: **the status report**, **the diet**, **the readme**
- **"Chirox, stop."** → ends the reading

**Read-me mode — the library.** Say **"Chirox, read me …"** and he reads
passage by passage, deaf while he speaks, then listens
briefly between passages — say anything (like "stop") in that gap to stop him.
He bookmarks where you stopped and resumes there next time; add "from the
beginning" to start over. The library (all local, public domain):

- *Daoism:* "read me the **tao te ching**" · "read me **chuang tzu**"
- *Confucianism:* "read me the **analects**" · "read me **mencius**"
- *Buddhism:* "read me the **dhammapada**" · "read me the **gospel of buddha**" · "read me the **light of asia**"
- *Strategy:* "read me the **art of war**"
- Plus any doc: "read me the **manual**", "the **guide**", "the **Kung Fu study guide**", "the **diet**"

(Plain "Chirox, read the manual" — without "me" — still streams continuously
in the background instead, and only a clear "Chirox, stop" interrupts it.)

While he's reading in background mode, he ignores everything except a stop
request — so speak the stop clearly. From the terminal you get more control:

```powershell
chirox library                            # show every local thing Chirox can read
chirox narrate 1yeartoShaolin.md            # read any file aloud
chirox narrate Diet\README.md --from 40     # resume where you stopped
chirox narrate 1yeartoShaolin.md --out manual.wav   # render to an audio file
chirox narrate --text "..." --pace 1.2      # slower, more deliberate pacing
```

Playback starts within seconds no matter how big the file is — he synthesizes
the next passage while speaking the current one.

### 4. Use Learning Mode for study

Open the desktop app and click **Learning Mode** when the work is reading,
reflection, or Dojo Record maintenance.

Learning Mode shows:

- a Master Chirox conversation panel
- the latest Piper speech and Whisper hearing activity
- the local reading library, with read-along text while Chirox speaks
- today's Mandarin character, pinyin, meaning, and reflection question
- a day picker with Daily Check-In and Mandarin Journal fields

When you save a day, Chirox does **not** silently rewrite history. It seals a new
version into the append-only Dojo Record, so future-you can see the path honestly.

### 5. Calibrate the Mirror ONCE before trusting it

Before you let numbers steer your training, measure the instrument itself:

```powershell
.\.venv\Scripts\python.exe -m chirox.vision.audit --source 0 --seconds 25 --stance horse
```

Stand full-body in frame and **hold horse stance as still as you can for the
whole grab**. Then look at `audit.json` in the printed output folder:

- `angles.left_knee.spread` (and `right_knee`) is the **noise floor** — you held
  still, so that wobble is the machine's error, not yours.
- **Spread ≤ ~5°:** trust the mirror; week-over-week changes bigger than that
  are real progress.
- **Spread ≥ ~15°:** don't trust stance numbers yet — fix framing/lighting and
  re-audit. Training still counts; the video record is always real.

---

## Part 2 — The daily loop (this is the actual training day)

### Morning — know where you stand (1 minute)

```powershell
chirox today
```

It tells you the day number, the phase, the focus, and whether a weekly or
monthly review is due. Voice works too: *"Chirox, what day is it?"*

### Training — let Chirox call the drills

Say **"Chirox, train me"** (or run `chirox train`). He chooses the stances the
Record shows you've practiced least, announces each one aloud — *"Horse
stance. Sixty seconds. Begin."* — watches through camera 0, and speaks
corrections while you hold: *"Sink lower; drop your center."* Every correction
comes from the deterministic geometry, never from an AI's opinion. After each
drill he tells you the honest number: percent of the hold spent in form, and
your most frequent fault. "Chirox, stop" ends the session.

Pick your own drills instead: `chirox train --stances horse,crane --seconds 45`

What "in form" means is written in code (`chirox/vision/stances.py`), from
published stance standards — your body is never the template, so a bad day can
never be enshrined as correct. When he can't see your full body he scores
nothing and says so.

### Training — record it, always

Open the live Mirror for real-time feedback while you work: double-click the
**Chirox** desktop icon. Training Mode starts the built-in webcam mirror on
launch. Pick the exercise/stance chips and keep the reference image visible so
you know what shape you are trying to make before the numbers judge anything.

Read the Mirror's three truth states like a traffic light:

- **Measured** (green) — the numbers are real, use them
- **Uncertain** (amber) — it can see *something* but not well; fix framing, don't trust numbers
- **No body** — it refuses to guess; step into frame

For the permanent record, record your session from the built-in webcam:

```powershell
# a static stance hold, with deterministic assessment:
chirox record --exercise horse_stance --stance horse --seconds 60

# a flowing sequence — measured, never graded:
chirox record --exercise eight_brocades --seconds 300
```

Every recording saves the video to your private archive and seals a manifest
into the Record. **Early sessions will look bad. Record them anyway.** The
embarrassing day-12 video is what makes the day-200 video mean something.
That is the whole point of the mirror that does not forget.

> The camera is shared — but the deck handles it: starting TRAIN or RECORD from
> the page stops the mirror automatically. Only when mixing terminal commands
> with the page do you need to stop the mirror yourself first.

### Evening — close the day (5 minutes)

```powershell
chirox log daily          # drops a prefilled template into Dojo\data\inbox
notepad <the printed path> # fill it honestly — 2 minutes
chirox log daily --file "<the printed path>"   # seal it forever
```

Then let the Master look at the evidence:

```powershell
chirox debrief --speak    # he speaks about what you actually did today
```

### Weekly rhythm

- **Sunday:** `chirox log weekly` (the system reminds you via `chirox today`)
- **Once or twice a week:** `chirox sage --speak --listen 8` — a short
  philosophical dialogue, grounded in the Tao Te Ching / Analects / Dhammapada.
  It builds your growth ledger: `chirox growth`
- **Monthly checkpoint days:** `chirox log monthly`

### Watching yourself improve

```powershell
chirox timeline                          # every recorded session, oldest first
chirox timeline --exercise horse_stance  # one exercise's whole arc
chirox verify                            # proof nobody (including you) edited history
```

---

## Part 3 — Reading the numbers without fooling yourself

**Horse stance (Ma Bu)** — the Mirror measures knee angles and back angles:
- knees ~90–100° = sunk properly; above 120° = too high; below 80° = collapsing
- back angle below ~150° = slouching

**Bow stance (Gong Bu)** — front knee 80–120°, rear leg ≥150° (near-straight).

Rules for dummies:

1. **`UNCERTAIN` is not failure.** It means the camera couldn't see your joints
   well. It is the system respecting you enough not to lie. Fix the framing.
2. **Compare weeks, not seconds.** Frame-to-frame wobble is noise (you measured
   exactly how much in Part 1). A knee angle that drops 10° over a month of
   holds is growth.
3. **Flowing forms get measured, never graded.** Range-of-motion numbers build
   your timeline; only a human teacher judges whether the form is *right*.
4. **The video outranks the numbers.** When in doubt, watch yourself.

---

## Part 4 — When something's wrong (60-second fixes)

| Symptom | Fix |
|---|---|
| "could not open video source" | Another program has the camera. Turn MIRROR off (or close OBS), retry. Relaunching from the desktop icon also sweeps stale camera holders. |
| Everything says `UNCERTAIN` | Feet or head out of frame, or backlit. Step back, light from the front. |
| The Master "is silent — he will not fabricate" | Ollama isn't running: `ollama serve` (and `ollama pull qwen2.5:14b-instruct` once). |
| The Ear doesn't hear you | Check the mic: `chirox listen --once --no-speak`, say something, read the transcript. Also: he can't hear you while he's talking. |
| Voice answers but never wakes | Say the name clearly at the start of the command: "Chirox, what day is it?" Check `chirox listen --self-test` passes. |
| Chirox wakes at weird times | Use full wake commands, not a bare name. The listener now only treats the name as intentional at the beginning of a command or after "hey/ok/okay." |
| Want a clean restart of the Ear | `.\Launch_Chirox_Voice.ps1` (replaces the running one) |
| **Shut him up NOW** | **Ctrl+Alt+0** — instantly silences whatever Chirox is saying, kills any reading or training session. Works from anywhere; no window focus needed. |
| A reading won't stop | Say "Chirox, stop" clearly — or `chirox narrate` sessions: Ctrl+C; from voice: `.\Launch_Chirox_Voice.ps1 -Stop` stops the ear, and the reading runs out alone (kill `python.exe -m chirox.narrator` in Task Manager if needed). |
| Is my record intact? | `chirox verify` — should say the chain holds. |

---

## Your first day, compressed

```powershell
chirox init --start <your-day-1>
.\Launch_Chirox_Voice.ps1 -Install
# calibrate: stand full-body, hold horse stance still through this:
.\.venv\Scripts\python.exe -m chirox.vision.audit --source 0 --seconds 25 --stance horse
chirox today
chirox record --exercise horse_stance --stance horse --seconds 60
chirox log daily            # fill it, ingest it
chirox debrief --speak
```

That's one complete, honest training day. Do it again tomorrow. The system
will remember every single one — that is its gift and its discipline.
