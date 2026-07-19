"""Chirox's open ear — the always-on wake-word daemon.

One process, always listening, fully local: microphone audio is segmented by a
deterministic energy gate (no model), each speech segment is transcribed by
faster-whisper on this machine, and nothing is acted on unless the segment
carries the wake word — "Chirox". Everything heard stays on this laptop; audio
that does not wake him is discarded.

Flow:

    mic → SpeechSegmenter (energy VAD, pure math)
        → Whisper transcript
        → wake match ("Chirox …")
        → route: local answer (day/standing), conversation or reflection with
          the Master (Ollama, streamed sentence by sentence, past sealed
          conversations recalled as memory), reading, or sleep
        → Piper speaks the reply (mic is paused while he talks, so he does not
          hear himself)

Honesty rules carry over: if Ollama is down the ear says the Master is silent —
it never fabricates an answer. The daemon seals nothing; talking to Chirox is
conversation, not evidence.

Run it:            python -m chirox.listener        (or: chirox listen)
Prove the loop:    python -m chirox.listener --self-test   (no mic needed)
One utterance:     python -m chirox.listener --once        (mic hardware check)
"""

from __future__ import annotations

import queue
import threading
import time

PANIC_HOTKEY = "ctrl+alt+0"

# --- wake word matching (pure) ---------------------------------------------------

# Bias Whisper toward the wake word — without this it drops "Chirox" as an
# unknown proper noun (proven by --self-test on 2026-07-02).
WHISPER_PROMPT = "The assistant's name is Chirox. The speaker may say: Chirox, what day is it?"

# Whisper spellings observed/expected for "Chirox" — matched space-insensitively.
# Live STT uses no wake prompt (avoids hallucination); these aliases catch soft mishears.
WAKE_ALIASES = [
    "chirox", "chi rox", "kairox", "kai rox", "kyrox", "chirocks",
    "shirox", "tyrox", "cheerocks", "chi rocks",
]
WAKE_PREFIXES = {"hey", "ok", "okay"}

_SLEEP_PHRASES = ["go to sleep", "stop listening", "shut down", "shutdown", "good night", "goodnight"]
_DAY_HINTS = ["what day", "which day", "where do i stand", "where am i", "day number"]
_REFLECT_HINTS = ["reflect", "look back", "how have i grown", "how far have i come",
                  "what have i learned", "where have i grown"]
_TRAIN_HINTS = ["train me", "call the training", "start training", "training call", "lets train", "let us train"]
_TRAINING_MODE_HINTS = ["training mode", "mirror mode", "body mode"]
_LEARNING_MODE_HINTS = ["learning mode", "study mode", "reading mode"]
_BROCADE_HINTS = [
    "eight brocades", "ba duan jin", "baduanjin", "brocades",
    "start eight brocades", "begin eight brocades", "start the brocades",
]
_ROUTINE_NEXT_HINTS = ["next phase", "next brocade", "next movement", "next exercise"]
_ROUTINE_STOP_HINTS = ["end routine", "seal the routine", "finish brocades", "stop brocades", "seal routine"]
_RECORD_STOP_HINTS = [
    "stop recording", "end recording", "finish recording", "cancel recording",
    "stop the recording", "seal the recording",
]
_RECORD_START_HINTS = [
    "start recording", "begin recording", "record me", "record this",
    "start a recording", "begin a recording",
]
_VERIFY_HINTS = [
    "how close am i", "how close", "am i in form", "am i matching",
    "what do you see", "verify me", "verify", "check my form", "check my stance",
    "score me", "what is my score",
]
_VERIFY_SEAL_HINTS = [
    "seal the match", "seal my form", "seal verification", "seal the verify",
    "save my score", "seal my score",
]
# Longest-first spoken aliases → (catalog key, hold?). Holds get a stance id.
_RECORD_EXERCISE_ALIASES = [
    ("one legged stance", "one_leg_stand", True),
    ("one leg stand", "one_leg_stand", True),
    ("one legged", "one_leg_stand", True),
    ("one leg", "one_leg_stand", True),
    ("horse stance", "horse", True),
    ("bow stance", "bow", True),
    ("crane stance", "crane", True),
    ("drop stance", "drop_stance", True),
    ("rest stance", "rest_stance", True),
    ("t stance", "t_stance", True),
    ("wall sit", "wall_sit", True),
    ("deep squat", "deep_squat_hold", True),
    ("half squat", "half_squat", True),
    ("squat hold", "squat_hold", True),
    ("cossack", "cossack_hold", True),
    ("side plank", "side_plank", True),
    ("superman", "superman_hold", True),
    ("standing tree", "standing_tree", True),
    ("horse guard", "horse_guard", True),
    ("wuji standing", "wuji_standing", True),
    ("wuji", "wuji_standing", True),
    ("eight brocades", "eight_brocades", False),
    ("ba duan jin", "eight_brocades", False),
    ("free training", "free_training", False),
    ("free train", "free_training", False),
    ("knee raises", "knee_raises", False),
    ("jumping jacks", "jumping_jacks", False),
    ("push ups", "pushups", False),
    ("pushups", "pushups", False),
    ("squats", "squats", False),
    ("plank", "plank", True),
    ("horse", "horse", True),
    ("crane", "crane", True),
    ("bow", "bow", True),
]
_WORD_NUMBERS = {
    "half": 0.5, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _normalize(text: str) -> str:
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in text.lower())
    return " ".join(cleaned.split())


def match_wake(text: str, aliases: list[str] | None = None) -> tuple[bool, str]:
    """Return (woken, command-after-the-wake-word).

    The wake word must be an intentional address: first words, or after a short
    address prefix like "hey". It is not matched in the middle of ordinary room
    speech.
    """
    aliases = aliases or WAKE_ALIASES
    norm = _normalize(text)
    if not norm:
        return False, ""
    words = norm.split()
    if words[0] in WAKE_PREFIXES:
        words = words[1:]
    for alias in sorted(aliases, key=lambda a: len(a.split()), reverse=True):
        alias_words = alias.split()
        if words[:len(alias_words)] == alias_words:
            return True, " ".join(words[len(alias_words):]).strip()
        if alias.replace(" ", "") == "".join(words[:len(alias_words)]):
            return True, " ".join(words[len(alias_words):]).strip()
    return False, ""


def _record_exercise_id(key: str, is_hold: bool) -> str:
    if not is_hold:
        return key
    if key.endswith("_stance") or "_" in key:
        return key
    return f"{key}_stance"


def parse_duration_seconds(text: str, default: int = 60) -> int:
    """Pull a recording length from speech. Default one minute."""
    import re

    norm = _normalize(text)
    if "thirty seconds" in norm or "half a minute" in norm or "half minute" in norm:
        return 30
    m = re.search(r"(\d+)\s*seconds?", norm)
    if m:
        return max(5, int(m.group(1)))
    m = re.search(r"(\d+)\s*minutes?", norm)
    if m:
        return max(5, int(m.group(1)) * 60)
    m = re.search(r"for\s+(half|one|two|three|four|five|six|seven|eight|nine|ten)\s+minutes?", norm)
    if m:
        n = _WORD_NUMBERS[m.group(1)]
        return max(5, int(n * 60))
    m = re.search(r"(half|one|two|three|four|five|six|seven|eight|nine|ten)\s+minutes?", norm)
    if m:
        n = _WORD_NUMBERS[m.group(1)]
        return max(5, int(n * 60))
    return default


def parse_record_request(command: str) -> dict:
    """Parse exercise + duration from a spoken record command. Pure."""
    norm = _normalize(command)
    for lead in ("please ", "would you ", "can you "):
        if norm.startswith(lead):
            norm = norm[len(lead):]
    rest = norm
    for lead in sorted(_RECORD_START_HINTS + ["record"], key=len, reverse=True):
        if rest == lead:
            rest = ""
            break
        if rest.startswith(lead + " "):
            rest = rest[len(lead):].strip()
            break
    for filler in ("of ", "a ", "an ", "the ", "my "):
        if rest.startswith(filler):
            rest = rest[len(filler):]
    seconds = parse_duration_seconds(rest if rest else norm, default=60)
    key = "free_training"
    is_hold = False
    matched = False
    haystack = rest or norm
    for phrase, catalog_key, hold in _RECORD_EXERCISE_ALIASES:
        if phrase in haystack:
            # Bare "record me" / "start recording" with no exercise stays free_training.
            if not rest and catalog_key != "free_training":
                continue
            key, is_hold, matched = catalog_key, hold, True
            break
    if key == "eight_brocades":
        exercise = "eight_brocades"
        stance = None
    elif key == "free_training":
        exercise = "free_training"
        stance = None
    else:
        exercise = _record_exercise_id(key, is_hold)
        stance = key if is_hold else None
    return {
        "exercise": exercise,
        "stance": stance,
        "seconds": seconds,
        "label": key.replace("_", " "),
        "matched_exercise": matched,
    }


def route(command: str) -> str:
    """Classify a spoken command. Pure, testable."""
    norm = _normalize(command)
    if any(p in norm for p in _SLEEP_PHRASES):
        return "sleep"
    if any(p in norm for p in _DAY_HINTS):
        return "day"
    if any(p in norm for p in _TRAINING_MODE_HINTS):
        return "mode_training"
    if any(p in norm for p in _LEARNING_MODE_HINTS):
        return "mode_learning"
    if any(p in norm for p in _ROUTINE_STOP_HINTS):
        return "routine_stop"
    if any(p in norm for p in _ROUTINE_NEXT_HINTS):
        return "routine_next"
    if any(p in norm for p in _BROCADE_HINTS):
        return "routine_brocades"
    if any(p in norm for p in _RECORD_STOP_HINTS):
        return "record_stop"
    if any(norm == p or norm.startswith(p + " ") or p in norm for p in _RECORD_START_HINTS):
        return "record_start"
    if norm.startswith("record "):
        req = parse_record_request(norm)
        if req["matched_exercise"] or "minute" in norm or "second" in norm:
            return "record_start"
    if any(p in norm for p in _VERIFY_SEAL_HINTS):
        return "verify_seal"
    if any(p in norm for p in _VERIFY_HINTS):
        return "verify_status"
    if any(p in norm for p in _TRAIN_HINTS):
        return "train"
    if any(p in norm for p in _REFLECT_HINTS):
        return "reflect"
    if "read" in norm.split():
        from chirox.narrator import resolve_readable

        if resolve_readable(norm) is not None:
            return "read"
    return "master"


def stop_requested(norm: str, woken: bool) -> bool:
    """During narration, is this transcript a genuine stop request?

    The mic hears the narrator through the speakers, so long transcripts are
    almost always echo. A stop is the wake word plus 'stop', or a very short
    bare 'stop' — echo of a document sentence containing 'stop' is long and
    is ignored.
    """
    words = norm.split()
    return "stop" in words and (woken or len(words) <= 3)


# --- live-exchange witness (the artifact that closes Gate 2) ----------------------


class LiveExchangeWitness:
    """A plain, inspectable log of a live spoken exchange with the ear.

    This is the artifact that turns "Chirox, what day is it?" from a claim into
    evidence: every transcript the ear heard, whether it was taken as an address,
    how it routed, and what Chirox answered. Pure text assembly — writing the
    markdown is the only side effect.

    It lives under ``Dojo/witness`` with a ``.local.`` infix so it is git-ignored
    by the existing rule (it carries the practitioner's own spoken words, which
    are private runtime data, never committed).
    """

    LIVE_CONTEXT = "the always-on ear on a live microphone (`chirox listen --once`)"

    def __init__(self, device=None, aliases=None, whisper_model=None,
                 samplerate: int | None = None, context: str | None = None):
        from datetime import datetime, timezone

        self.started_at = datetime.now(timezone.utc)
        self.device = device
        self.aliases = list(aliases or WAKE_ALIASES)
        self.whisper_model = whisper_model
        self.samplerate = samplerate
        self.context = context or self.LIVE_CONTEXT
        self.entries: list[dict] = []

    def record(self, *, heard: str, woken: bool, command: str = "", route: str = "",
               answer: str = "", spoken: bool = False, note: str = "") -> dict:
        from datetime import datetime, timezone

        entry = {
            "at": datetime.now(timezone.utc).isoformat(),
            "heard": heard,
            "woken": bool(woken),
            "command": command,
            "route": route,
            "answer": answer,
            "spoken": bool(spoken),
            "note": note,
        }
        self.entries.append(entry)
        return entry

    @property
    def woke(self) -> bool:
        """Was Chirox ever actually addressed (wake word matched)?"""
        return any(e["woken"] for e in self.entries)

    @property
    def answered(self) -> bool:
        """Did an addressed exchange produce a spoken/printed answer?"""
        return any(e["woken"] and e["command"] and e["answer"] for e in self.entries)

    def verdict(self) -> str:
        if self.answered:
            return "PASS — the wake word was heard and an answer was produced."
        if self.woke:
            return "PARTIAL — the wake word was heard, but no answer was produced."
        if self.entries:
            return "NO WAKE — audio was heard and transcribed, but never as an address to Chirox."
        return "NO AUDIO — nothing was transcribed."

    def render(self) -> str:
        lines = ["# Chirox Live Exchange Witness"]
        lines.append(f"## {self.started_at.strftime('%Y-%m-%d %H:%M:%SZ')}")
        lines.append("")
        lines.append(f"A recorded spoken exchange with {self.context}. Private "
                     "runtime data — the practitioner's own words — git-ignored, "
                     "not committed.")
        lines.append("")
        lines.append("## Setup")
        lines.append(f"- device: {self.device if self.device is not None else 'default'}")
        lines.append(f"- whisper model: {self.whisper_model or 'default'}")
        lines.append(f"- samplerate: {self.samplerate or 'n/a'}")
        lines.append(f"- wake aliases: {', '.join(self.aliases)}")
        lines.append("")
        lines.append("## What the ear heard")
        if not self.entries:
            lines.append("- (nothing transcribed)")
        for i, e in enumerate(self.entries, 1):
            when = e["at"][11:19]
            lines.append(f"{i}. [{when}] heard: \"{e['heard']}\"")
            if e["woken"]:
                routed = f" → route: {e['route']}" if e["route"] else ""
                lines.append(f"   - woken: yes → command: \"{e['command']}\"{routed}")
                if e["answer"]:
                    verb = "spoke" if e["spoken"] else "printed"
                    lines.append(f"   - Chirox {verb}: \"{e['answer']}\"")
            else:
                lines.append("   - woken: no (not taken as an address to Chirox)")
            if e["note"]:
                lines.append(f"   - note: {e['note']}")
        lines.append("")
        lines.append("## Verdict")
        lines.append(self.verdict())
        lines.append("")
        return "\n".join(lines)

    def default_path(self):
        from chirox.config import REPO_ROOT

        stamp = self.started_at.strftime("%Y%m%d_%H%M%S")
        return REPO_ROOT / "Dojo" / "witness" / f"live_exchange_{stamp}.local.md"

    def write(self, path=None):
        from pathlib import Path

        target = Path(path) if path else self.default_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.render(), encoding="utf-8")
        return target


# --- energy-gate speech segmenter (pure state machine) ----------------------------


class SpeechSegmenter:
    """Deterministic voice-activity gate over fixed-size audio blocks.

    Calibrates a noise floor from the first ``calib_blocks`` blocks, then opens
    on ``start_blocks`` consecutive loud blocks and closes after ``end_blocks``
    quiet ones. A short pre-roll keeps word onsets. While idle, quiet RMS
    samples slowly refresh the threshold so HVAC/TV changes do not freeze the
    gate forever. No neural VAD — the same input always segments the same way
    for a given threshold path.
    """

    def __init__(self, calib_blocks: int = 33, start_blocks: int = 3, end_blocks: int = 25,
                 min_blocks: int = 12, max_blocks: int = 500, pre_roll: int = 8,
                 threshold_ratio: float = 3.5, min_threshold: float = 0.01,
                 threshold: float | None = None,
                 recalib_quiet_blocks: int = 80, recalib_every_blocks: int = 400):
        self.calib_blocks = calib_blocks
        self.start_blocks = start_blocks
        self.end_blocks = end_blocks
        self.min_blocks = min_blocks
        self.max_blocks = max_blocks
        self.pre_roll = pre_roll
        self.threshold_ratio = threshold_ratio
        self.min_threshold = min_threshold
        self.threshold = threshold  # preset skips calibration (read-me windows)
        self.recalib_quiet_blocks = recalib_quiet_blocks
        self.recalib_every_blocks = recalib_every_blocks
        self._calib: list[float] = []
        self._quiet_rms: list[float] = []
        self._blocks_since_recalib = 0
        self._recent: list = []       # pre-roll ring buffer of (block, rms)
        self._active: list = []       # blocks of the in-progress segment
        self._loud_run = 0
        self._quiet_run = 0
        self._in_speech = False
        self.last_recalibrated = False

    def reset(self) -> None:
        """Drop any in-progress speech (used after Chirox talks over the room)."""
        # rebind, don't clear: a just-returned segment may still reference _active
        self._recent = []
        self._active = []
        self._loud_run = 0
        self._quiet_run = 0
        self._in_speech = False

    @staticmethod
    def _rms(block) -> float:
        import numpy as np

        return float(np.sqrt(np.mean(np.square(block, dtype="float64"))))

    def _floor_from(self, samples: list[float]) -> float:
        return max((sum(samples) / len(samples)) * self.threshold_ratio, self.min_threshold)

    def _maybe_recalibrate(self, rms: float, loud: bool) -> None:
        """Slowly refresh the noise floor from quiet idle blocks."""
        self.last_recalibrated = False
        if self.threshold is None or self._in_speech:
            return
        if not loud:
            self._quiet_rms.append(rms)
            if len(self._quiet_rms) > self.recalib_quiet_blocks:
                self._quiet_rms.pop(0)
        self._blocks_since_recalib += 1
        if (self._blocks_since_recalib < self.recalib_every_blocks
                or len(self._quiet_rms) < max(10, self.recalib_quiet_blocks // 2)):
            return
        fresh = self._floor_from(self._quiet_rms)
        # Blend so a door slam does not yank the gate.
        self.threshold = (0.65 * self.threshold) + (0.35 * fresh)
        self._blocks_since_recalib = 0
        self.last_recalibrated = True

    def push(self, block):
        """Feed one audio block; returns a finished segment (list of blocks) or None."""
        rms = self._rms(block)

        if self.threshold is None:
            self._calib.append(rms)
            if len(self._calib) >= self.calib_blocks:
                self.threshold = self._floor_from(self._calib)
            return None

        loud = rms > self.threshold
        self._maybe_recalibrate(rms, loud)
        if not self._in_speech:
            self._recent.append(block)
            if len(self._recent) > self.pre_roll:
                self._recent.pop(0)
            self._loud_run = self._loud_run + 1 if loud else 0
            if self._loud_run >= self.start_blocks:
                self._in_speech = True
                self._active = list(self._recent)
                self._recent = []
                self._quiet_run = 0
            return None

        self._active.append(block)
        self._quiet_run = 0 if loud else self._quiet_run + 1
        if self._quiet_run >= self.end_blocks or len(self._active) >= self.max_blocks:
            segment = self._active
            self.reset()
            if len(segment) >= self.min_blocks:
                return segment
        return None


# --- the ear -----------------------------------------------------------------------


class ChiroxEar:
    """The always-on loop: listen, wake, answer, keep listening."""

    SAMPLERATE = 16000
    BLOCK_MS = 30
    # ~6s of 30ms blocks. While Whisper runs on the main thread the callback
    # keeps firing — bound the queue and drop the oldest so backlog cannot grow.
    MAX_QUEUE_BLOCKS = 200

    def __init__(self, config=None, device=None, aliases: list[str] | None = None,
                 speak_replies: bool = True):
        from chirox.config import Config

        self.config = config or Config.load()
        self.device = device
        self.aliases = aliases or WAKE_ALIASES
        self.speak_replies = speak_replies
        self._voice = None
        self._narrator = None
        self._stream = None
        self._queue: queue.Queue = queue.Queue(maxsize=self.MAX_QUEUE_BLOCKS)
        self._awaiting_until = 0.0   # retained for old sessions; bare wake no longer opens commands
        self._threshold: float | None = None  # room noise floor, once calibrated
        self._reset_segmenter = False
        self._panic = threading.Event()  # Ctrl+Alt+0: silence everything NOW
        self._chat: list[tuple[str, str]] = []  # this sitting's conversation turns
        self._witness: LiveExchangeWitness | None = None  # opt-in exchange log
        self._last_answer = ""    # the reply to the command being handled
        self._exchange_done = False  # an addressed exchange completed (for --once)
        self._overflow_noted = False
        self.running = False

    def panic(self) -> None:
        """The kill switch: abort current speech, kill any narration/training."""
        self._panic.set()
        try:
            import sounddevice as sd

            sd.stop()
        except Exception:
            pass
        try:
            from chirox.narrator import stop_narration

            if stop_narration():
                print("[ear] hotkey: narration/training killed")
        except Exception:
            pass
        print(f"[ear] silenced ({PANIC_HOTKEY})")

    @property
    def voice(self):
        if self._voice is None:
            from chirox.voice import Voice

            self._voice = Voice(piper_voice=self.config.piper_voice,
                                whisper_model=self.config.whisper_model,
                                pace=self.config.speech_pace)
        return self._voice

    # --- audio plumbing ---------------------------------------------------------

    def _block_frames(self) -> int:
        return int(self.SAMPLERATE * self.BLOCK_MS / 1000)

    def _callback(self, indata, frames, t, status):
        if status and not self._overflow_noted:
            # PortAudio overflow/underflow — note once so logs stay readable.
            print(f"[ear] (audio status: {status})")
            self._overflow_noted = True
        block = indata[:, 0].copy()
        try:
            self._queue.put_nowait(block)
        except queue.Full:
            try:
                self._queue.get_nowait()  # drop oldest — prefer the present moment
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(block)
            except queue.Full:
                pass

    def _say(self, text: str) -> None:
        """Speak with the mic paused — Chirox must not hear himself."""
        print(f"[ear] chirox: {text}")
        self._last_answer = text  # the single choke point for short spoken replies
        if not self.speak_replies:
            return
        if self._stream is not None:
            try:
                self._stream.stop()
            except Exception:
                pass
        try:
            self.voice.speak(text)
        except Exception as exc:  # keep listening even if the mouth fails
            print(f"[ear] (voice playback failed: {exc})")
        finally:
            self._drain_queue()
            if self._stream is not None:
                try:
                    self._stream.start()
                except Exception as exc:
                    print(f"[ear] (mic restart failed: {exc})")
            self._reset_segmenter = True

    @property
    def narrator(self):
        if self._narrator is None:
            from chirox.narrator import Narrator

            self._narrator = Narrator()
        return self._narrator

    # --- read-me mode -------------------------------------------------------------

    def _drain_queue(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def _play_passage(self, text: str) -> None:
        """Speak one passage in the narrator voice with the mic fully off."""
        import sounddevice as sd

        if self._stream is not None:
            self._stream.stop()
        try:
            sd.play(self.narrator.synth(text), self.narrator.samplerate)
            sd.wait()
        except Exception as exc:
            print(f"[ear] (narration playback failed: {exc})")

    def _listen_window(self, seconds: float = 4.0, max_extra: float = 8.0) -> str:
        """Between passages: open the mic briefly; return a transcript or ''."""
        if self._stream is None:
            return ""
        self._drain_queue()
        try:
            self._stream.start()
        except Exception as exc:
            print(f"[ear] (listen window mic failed: {exc})")
            return ""
        seg = SpeechSegmenter(threshold=self._threshold or 0.01,
                              start_blocks=2, end_blocks=15, min_blocks=6)
        deadline = time.monotonic() + seconds
        hard_stop = deadline + max_extra
        try:
            while time.monotonic() < (hard_stop if seg._in_speech else deadline):
                try:
                    block = self._queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                segment = seg.push(block)
                if segment is not None:
                    return self._transcribe_segment(segment)
            return ""
        finally:
            try:
                self._stream.stop()
            except Exception:
                pass

    def read_me(self, label: str, path, restart: bool = False) -> None:
        """Passage-by-passage reading: deaf during a passage (by design), a short
        listening window after each one, and a bookmark that survives restarts."""
        from chirox.narrator import prepare, reading_progress, set_reading_progress

        chunks = prepare(path)
        if not chunks:
            self._say(f"There is nothing speakable in {label}.")
            return
        key = getattr(path, "name", str(path))
        i = 0 if restart else int(reading_progress().get(key, 0))
        if i >= len(chunks):
            i = 0
        self._panic.clear()
        if i > 0:
            self._say(f"Continuing {label} where we left off.")
        else:
            self._say(f"{label}. I will read it to you, all of it. "
                      "Say stop whenever you need silence.")
        try:
            while i < len(chunks):
                if self._panic.is_set():
                    # Ctrl+Alt+0: die silently — the whole point is no more sound
                    print(f"[read-me] killed by hotkey; bookmarked at passage {i}")
                    return
                print(f"[read-me {i + 1}/{len(chunks)}] {chunks[i][:64]}")
                self._play_passage(chunks[i])
                i += 1
                set_reading_progress(key, i if i < len(chunks) else 0)
                heard = self._listen_window()
                if heard:
                    norm = _normalize(heard)
                    print(f'[read-me] heard between passages: "{heard}"')
                    if "stop" in norm.split() or route(norm) == "sleep":
                        self._say(f"Marked where we stopped. Say — read me {label} — "
                                  "and I continue from there.")
                        return
            self._say(f"That completes {label}.")
        finally:
            self._drain_queue()
            if self._stream is not None:
                self._stream.start()

    def _transcribe_segment(self, segment) -> str:
        import numpy as np
        import soundfile as sf

        from chirox.config import VOICE_DIR

        wav = VOICE_DIR / "_ear_segment.wav"
        wav.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(wav), np.concatenate(segment), self.SAMPLERATE)
        # No wake-word prompt in the live room: biasing Whisper toward "Chirox"
        # can hallucinate the wake word from unrelated speech.
        return self.voice.transcribe(wav)

    # --- command handling ---------------------------------------------------------

    def _answer_day(self) -> str:
        from chirox.calendar import dojo_day

        d = dojo_day(self.config.practice_start_date)
        return d.headline()

    def _cockpit_post(self, path: str, body: dict | None = None) -> dict:
        """Talk to the local mirror API. Honest failure if the cockpit is down."""
        import json
        import urllib.error
        import urllib.request

        url = f"http://127.0.0.1:8765{path}"
        data = json.dumps(body or {}).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            return {"ok": False, "error": f"mirror not reachable ({exc.reason})"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _cockpit_get(self, path: str) -> dict:
        import json
        import urllib.error
        import urllib.request

        url = f"http://127.0.0.1:8765{path}"
        try:
            with urllib.request.urlopen(url, timeout=4) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            return {"ok": False, "active": False, "error": f"mirror not reachable ({exc.reason})"}
        except Exception as exc:
            return {"ok": False, "active": False, "error": str(exc)}

    def _converse_and_speak(self, question: str, reflect: bool = False) -> None:
        """Conversation with the Master: streamed sentence by sentence, so speech
        begins with his first sentence, not after his last. The mic stays paused
        for the whole reply (he must not hear himself), whatever was actually
        said is sealed — even if the stream dies mid-thought."""
        from chirox.master.brain import MasterUnavailable, converse_stream, seal_exchange

        spoken: list[str] = []
        if self._stream is not None:
            self._stream.stop()
        try:
            for sentence in converse_stream(self.config, question=question,
                                            history=self._chat, reflect=reflect):
                print(f"[ear] chirox: {sentence}")
                spoken.append(sentence)
                if self.speak_replies:
                    try:
                        self.voice.speak(sentence)
                    except Exception as exc:  # keep the reply going if the mouth stumbles
                        print(f"[ear] (voice playback failed: {exc})")
        except MasterUnavailable as exc:
            if not spoken:
                self._say(f"The Master is silent — he will not fabricate. {exc}")
                return
            print(f"[ear] (stream ended early: {exc})")
        finally:
            if self._stream is not None:
                self._drain_queue()
                self._stream.start()
            self._reset_segmenter = True
        if not spoken:
            self._say("The Master is silent — he gave no words.")
            return
        answer = " ".join(spoken)
        self._last_answer = answer
        self._chat.append((question, answer))
        self._chat = self._chat[-8:]  # a sitting's worth of context; the codex holds the rest
        try:
            seal_exchange(question, answer, self.config)
        except Exception as exc:  # logging must never silence the conversation
            print(f"[ear] (could not seal exchange: {exc})")

    def handle_command(self, command: str) -> bool:
        """Execute one spoken command. Returns False when the ear should shut down."""
        kind = route(command)
        if kind == "sleep":
            self._say("Resting the ear. Train well.")
            return False
        if kind == "day":
            self._say(self._answer_day())
            return True
        if kind == "mode_training":
            from chirox.activity import set_mode

            set_mode("training")
            self._say("Training mode.")
            return True
        if kind == "mode_learning":
            from chirox.activity import set_mode

            set_mode("learning")
            self._say("Learning mode.")
            return True
        if kind == "train":
            import subprocess
            import sys as _sys

            from chirox.config import REPO_ROOT

            from chirox.narrator import claim_narration_lock

            self._say("Training call. Stand in front of the camera; I will call the drills.")
            flags = 0x08000000 if _sys.platform == "win32" else 0
            proc = subprocess.Popen([_sys.executable, "-m", "chirox.trainer"], cwd=str(REPO_ROOT),
                                    creationflags=flags, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            # Claim the shared lock immediately so early "Chirox" echo is ignored.
            claim_narration_lock(proc.pid)
            print(f"[ear] training session started (pid {proc.pid})")
            return True
        if kind == "routine_brocades":
            res = self._cockpit_post("/api/routine/start", {"routine_key": "eight_brocades_ste"})
            if res.get("ok") is False and res.get("error"):
                self._say(f"Could not start the brocades. {res['error']}. Open the Chirox mirror first.")
            else:
                self._say("Eight Brocades. Follow Wireguy. Say next phase, or end routine to seal the log.")
            return True
        if kind == "routine_next":
            res = self._cockpit_post("/api/routine/next", {})
            if res.get("ok") is False:
                self._say("No routine is active. Say Chirox, Eight Brocades to begin.")
            else:
                self._say(res.get("phase_label") or "next phase")
            return True
        if kind == "routine_stop":
            res = self._cockpit_post("/api/routine/stop", {
                "routine_key": "eight_brocades_ste", "seal": True, "source": "0",
            })
            if res.get("ok") and res.get("sealed"):
                totals = (res.get("summary") or {}).get("totals") or {}
                self._say(
                    f"Routine sealed. {totals.get('phases_completed', 0)} phases, "
                    f"{totals.get('reps_total', 0)} reps. Forever in the record."
                )
            else:
                self._say(res.get("error") or "No routine was active to seal.")
            return True
        if kind == "record_stop":
            res = self._cockpit_post("/api/record/stop", {})
            if res.get("stopped"):
                note = res.get("note") or "Recording stopped."
                self._say(note if "sealed" in note.lower() else
                          "Recording stopped. Video kept; say start recording when you want another.")
            else:
                self._say(res.get("note") or res.get("error") or "Nothing was recording.")
            return True
        if kind == "verify_status":
            res = self._cockpit_get("/api/verify/status")
            if not res.get("active"):
                self._say(res.get("error") or "Open the mirror. Stand a shape. Then ask again.")
                return True
            last = (res.get("last") or {}).get("target") or {}
            label = last.get("label") or res.get("label") or "the shape"
            if last.get("uncertain"):
                self._say(f"{label}. Uncertain — I cannot see the joints clearly.")
                return True
            score = last.get("score")
            mean = res.get("mean_score")
            band = "in band" if last.get("in_band") else "out of band"
            corr = (last.get("corrections") or [None])[0]
            parts = [f"{label}: {int(score)} percent, {band}." if score is not None else f"{label}."]
            if mean is not None:
                parts.append(f"Session mean {int(mean)}.")
            if corr and not last.get("in_band"):
                parts.append(corr)
            self._say(" ".join(parts))
            return True
        if kind == "verify_seal":
            res = self._cockpit_post("/api/verify/seal", {"source": "0"})
            if res.get("ok") and res.get("sealed"):
                s = res.get("summary") or {}
                mean = s.get("mean_score")
                self._say(
                    f"Verification sealed. {s.get('label') or 'Session'}. "
                    f"Mean {int(mean) if mean is not None else '—'} percent. Forever in the record."
                )
            else:
                self._say(res.get("error") or "Nothing to seal yet. Train first.")
            return True
        if kind == "record_start":
            from chirox.activity import set_mode

            set_mode("training")
            req = parse_record_request(command)
            # Do not POST /api/session/start here — that replaces the live
            # session and drops the Wireguy websocket. begin_recording tees
            # onto the mirror that is already open.
            res = self._cockpit_post("/api/record/start", {
                "exercise": req["exercise"],
                "source": "0",
                "seconds": req["seconds"],
                "stance": req["stance"],
            })
            if res.get("ok") is False:
                self._say(
                    f"I could not start recording. {res.get('error') or 'unknown error'}. "
                    "Open the Chirox window so Wireguy is awake."
                )
            else:
                secs = int(req["seconds"])
                if secs % 60 == 0:
                    span = f"{secs // 60} minute" + ("s" if secs // 60 != 1 else "")
                else:
                    span = f"{secs} seconds"
                self._say(
                    f"Recording {req['label']} for {span}. "
                    "Wireguy stays with you. Say Chirox, stop recording when you are done."
                )
            return True
        if kind == "reflect":
            self._converse_and_speak(command, reflect=True)
            return True
        if kind == "read":
            from chirox.narrator import resolve_readable, spawn_narration

            label, path = resolve_readable(command)
            if "me" in _normalize(command).split():
                # "read me …" — passage mode: deaf while reading, a listening
                # window between passages, bookmark kept.
                self.read_me(label, path, restart="beginning" in command or "start over" in command)
                return True
            self._say(f"Reading {label}. Say — Chirox, stop — when you have heard enough.")
            pid = spawn_narration(path)
            print(f"[ear] narration started (pid {pid}): {path}")
            return True
        self._converse_and_speak(command)
        return True

    def _record_witness(self, *, heard: str, woken: bool, command: str = "",
                        route: str = "", note: str = "") -> None:
        """Append one line to the live-exchange witness, if one is active.

        Witnessing must never disturb the ear — a failed log is printed, not
        raised."""
        if self._witness is None:
            return
        try:
            self._witness.record(
                heard=heard, woken=woken, command=command, route=route,
                answer=self._last_answer if woken and command else "",
                spoken=self.speak_replies, note=note,
            )
        except Exception as exc:
            print(f"[ear] (witness record failed: {exc})")

    def handle_transcript(self, text: str) -> bool:
        """Wake/command state machine over one transcript. Returns False to stop."""
        text = text.strip()
        if not text:
            return True
        try:
            from chirox.activity import update_activity

            update_activity(last_heard=text)
        except Exception:
            pass
        woken, command = match_wake(text, self.aliases)

        # While a narration plays, the speakers are saying things like "Chirox" —
        # act only on a stop request, ignore everything else (it is mostly echo).
        from chirox.narrator import narration_pid, stop_narration

        if narration_pid() is not None:
            if stop_requested(_normalize(text), woken):
                stop_narration()
                self._say("Reading stopped.")
                self._record_witness(heard=text, woken=woken, note="stop during narration")
            else:
                print(f'[ear] (narration playing) "{text}"')
                self._record_witness(heard=text, woken=False, note="narration echo ignored")
            return True

        if woken:
            print(f'[ear] wake word heard: "{text}"')
            if command:
                self._last_answer = ""            # this command's own reply
                kind = route(command)
                keep_going = self.handle_command(command)
                self._record_witness(heard=text, woken=True, command=command, route=kind)
                self._exchange_done = True        # an addressed exchange completed
                return keep_going
            self._say("Say my name and the command together.")
            self._record_witness(heard=text, woken=True, note="bare wake — no command")
            self._awaiting_until = 0.0
            return True
        print(f'[ear] (not for me) "{text}"')
        self._record_witness(heard=text, woken=False, note="not addressed")
        return True

    # --- main loop ------------------------------------------------------------------

    def _open_input_stream(self):
        import sounddevice as sd

        return sd.InputStream(
            samplerate=self.SAMPLERATE, channels=1, dtype="float32",
            blocksize=self._block_frames(), device=self.device, callback=self._callback,
        )

    def run(self, once: bool = False, witness: "LiveExchangeWitness | None" = None) -> None:
        self._witness = witness
        self._exchange_done = False
        self.running = True
        try:
            import keyboard as kb

            kb.add_hotkey(PANIC_HOTKEY, self.panic)
            print(f"[ear] kill switch armed: {PANIC_HOTKEY} silences Chirox instantly")
        except Exception as exc:  # hotkey is a convenience, never a blocker
            print(f"[ear] (kill-switch hotkey unavailable: {exc})")
        print(f"[ear] awake — wake word: 'Chirox' (device: {self.device if self.device is not None else 'default'})")

        # Preflight mouth + ears before greeting — honest downtime beats a silent hang.
        ready = self.voice.preflight()
        if not ready["ok"]:
            print(f"[ear] voice not ready: {ready['error']}")
            if ready["piper"] and not ready["whisper"]:
                self._say("My hearing is not ready. Check the Whisper model on this machine.")
            elif ready["whisper"] and not ready["piper"]:
                print("[ear] Piper is unavailable — cannot speak. Hearing alone is not enough to run.")
            else:
                print("[ear] mouth and ears are unavailable — resting.")
            self.running = False
            return

        print("[ear] calibrating room noise (~1s of quiet, please)…")
        reconnects = 0
        max_reconnects = 0 if once else 12
        try:
            while self.running:
                segmenter = SpeechSegmenter()
                self._drain_queue()
                try:
                    self._stream = self._open_input_stream()
                except Exception as exc:
                    print(f"[ear] microphone could not open: {exc}")
                    if once or reconnects >= max_reconnects:
                        break
                    reconnects += 1
                    time.sleep(2.0)
                    continue
                try:
                    with self._stream:
                        if reconnects == 0:
                            self._say("I am here.")
                        else:
                            print(f"[ear] microphone recovered (attempt {reconnects})")
                            self._say("I am listening again.")
                        while self.running:
                            try:
                                block = self._queue.get(timeout=1.0)
                            except queue.Empty:
                                continue
                            if self._reset_segmenter:
                                segmenter.reset()
                                self._reset_segmenter = False
                                continue
                            segment = segmenter.push(block)
                            if segmenter.threshold is not None and segmenter._calib:
                                segmenter._calib = []
                                self._threshold = segmenter.threshold
                                print(f"[ear] noise floor set (threshold {segmenter.threshold:.4f}); listening.")
                            if segmenter.last_recalibrated:
                                self._threshold = segmenter.threshold
                                print(f"[ear] noise floor refreshed (threshold {segmenter.threshold:.4f})")
                            if segment is None:
                                continue
                            try:
                                text = self._transcribe_segment(segment)
                            except Exception as exc:
                                print(f"[ear] (transcription failed: {exc})")
                                continue
                            keep_going = self.handle_transcript(text)
                            if once and self._exchange_done:
                                self.running = False
                                break
                            if not keep_going:
                                self.running = False
                                break
                except KeyboardInterrupt:
                    print("\n[ear] interrupted — resting.")
                    break
                except Exception as exc:
                    print(f"[ear] microphone stream lost: {exc}")
                    if once or reconnects >= max_reconnects:
                        break
                    reconnects += 1
                    time.sleep(2.0)
                    continue
                break
        finally:
            self._stream = None
        if self._witness is not None:
            try:
                path = self._witness.write()
                print(f"[ear] witness written: {path}")
                print(f"[ear] {self._witness.verdict()}")
            except Exception as exc:
                print(f"[ear] (witness write failed: {exc})")
        self.running = False


# --- self test (no microphone needed) ------------------------------------------------


def self_test(witness: bool = False) -> bool:
    """Prove the loop TTS→STT→wake→route→**answer** with Chirox's own mouth as
    the speaker — the whole chain except the physical mic. With ``witness`` the
    proof is written to an inspectable log, exactly as the live ear writes one.

    Runs two STT passes: with the wake prompt (stable unit proof) and without
    (matches the live room). PASS requires the prompted path; the unprompted
    path is reported honestly so drift is visible.
    """
    from chirox.voice import Voice, VoiceNotReady

    try:
        v = Voice()
        ready = v.preflight()
    except Exception as exc:
        print(f"[self-test] FAIL — voice preflight crashed: {exc}")
        return False
    if not ready["ok"]:
        print(f"[self-test] FAIL — voice not ready: {ready['error']}")
        return False

    phrase = "Chirox, what day is it today?"
    print(f'[self-test] speaking to a wav: "{phrase}"')
    try:
        wav = v.speak(phrase, play=False)
    except VoiceNotReady as exc:
        print(f"[self-test] FAIL — could not speak: {exc}")
        return False

    heard_prompted = v.transcribe(wav, initial_prompt=WHISPER_PROMPT)
    heard_live = v.transcribe(wav, initial_prompt=None)
    print(f'[self-test] whisper (prompted): "{heard_prompted}"')
    print(f'[self-test] whisper (live path): "{heard_live}"')

    woken, command = match_wake(heard_prompted)
    woken_live, _ = match_wake(heard_live)
    kind = route(command) if woken else "-"
    answer = ""
    if woken and kind == "day":
        try:
            answer = ChiroxEar(speak_replies=False)._answer_day()
        except Exception as exc:
            print(f"[self-test] (day answer failed: {exc})")
    print(f"[self-test] wake={woken} live_wake={woken_live} command={command!r} route={kind}")
    print(f'[self-test] day answer:       "{answer}"')
    if woken and not woken_live:
        print("[self-test] note: live (unprompted) STT missed the wake — room path is harder; aliases help.")
    ok = bool(woken and kind == "day" and answer.strip())
    if witness:
        log = LiveExchangeWitness(device="self-test (no mic)",
                                  whisper_model=v._whisper_name,
                                  samplerate=ChiroxEar.SAMPLERATE,
                                  context="the TTS→STT self-test (Chirox's own mouth, no microphone)")
        log.record(heard=heard_prompted, woken=woken, command=command, route=kind,
                   answer=answer, spoken=False,
                   note=f"TTS→STT self-test; live_path_wake={woken_live}")
        path = log.write()
        print(f"[self-test] witness written: {path}")
    print(f"[self-test] {'PASS' if ok else 'FAIL'}")
    return ok


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Chirox always-on wake-word ear")
    ap.add_argument("--device", type=int, default=None, help="input device index (see --list-devices)")
    ap.add_argument("--list-devices", action="store_true", help="list audio devices and exit")
    ap.add_argument("--self-test", action="store_true", help="prove TTS→STT→wake→answer without a mic")
    ap.add_argument("--once", action="store_true", help="hold until one addressed exchange completes, then exit")
    ap.add_argument("--no-speak", action="store_true", help="print replies instead of speaking them")
    ap.add_argument("--witness", action="store_true",
                    help="write an inspectable witness log of the exchange (implied by --once)")
    args = ap.parse_args(argv)

    if args.list_devices:
        import sounddevice as sd

        print(sd.query_devices())
        return 0
    if args.self_test:
        return 0 if self_test(witness=args.witness) else 1

    ear = ChiroxEar(device=args.device, speak_replies=not args.no_speak)
    witness = None
    if args.once or args.witness:
        witness = LiveExchangeWitness(device=args.device, aliases=ear.aliases,
                                      whisper_model=ear.config.whisper_model,
                                      samplerate=ChiroxEar.SAMPLERATE)
    ear.run(once=args.once, witness=witness)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
