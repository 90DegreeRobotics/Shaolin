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
        → route: local answer (day/standing), Master debrief (Ollama), or sleep
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
WAKE_ALIASES = [
    "chirox", "kairox", "cairox", "kyrox", "chyrox", "chirocks", "kirox",
    "cheerox", "shirox", "chirax", "kairos", "chi rox", "kai rox", "sky rox",
]

_SLEEP_PHRASES = ["go to sleep", "stop listening", "shut down", "shutdown", "good night", "goodnight"]
_DAY_HINTS = ["what day", "which day", "where do i stand", "where am i", "day number"]
_TRAIN_HINTS = ["train me", "call the training", "start training", "training call", "lets train", "let us train"]


def _normalize(text: str) -> str:
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in text.lower())
    return " ".join(cleaned.split())


def match_wake(text: str, aliases: list[str] | None = None) -> tuple[bool, str]:
    """Return (woken, command-after-the-wake-word).

    Matching is case-, punctuation- and space-insensitive so "Kai Rox," still
    wakes him. The remainder is whatever was said after the name.
    """
    aliases = aliases or WAKE_ALIASES
    norm = _normalize(text)
    if not norm:
        return False, ""
    words = norm.split()
    squashed = "".join(words)
    for alias in sorted((a.replace(" ", "") for a in aliases), key=len, reverse=True):
        idx = squashed.find(alias)
        if idx == -1:
            continue
        # walk words until the alias is fully covered, then the rest is the command
        consumed = 0
        for w_i, w in enumerate(words):
            consumed += len(w)
            if consumed >= idx + len(alias):
                return True, " ".join(words[w_i + 1:]).strip()
        return True, ""
    return False, ""


def route(command: str) -> str:
    """Classify a spoken command: 'sleep' | 'day' | 'read' | 'master'. Pure, testable."""
    norm = _normalize(command)
    if any(p in norm for p in _SLEEP_PHRASES):
        return "sleep"
    if any(p in norm for p in _DAY_HINTS):
        return "day"
    if any(p in norm for p in _TRAIN_HINTS):
        return "train"
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


# --- energy-gate speech segmenter (pure state machine) ----------------------------


class SpeechSegmenter:
    """Deterministic voice-activity gate over fixed-size audio blocks.

    Calibrates a noise floor from the first ``calib_blocks`` blocks, then opens
    on ``start_blocks`` consecutive loud blocks and closes after ``end_blocks``
    quiet ones. A short pre-roll keeps word onsets. No model, no magic — the
    same input always segments the same way.
    """

    def __init__(self, calib_blocks: int = 33, start_blocks: int = 3, end_blocks: int = 25,
                 min_blocks: int = 12, max_blocks: int = 500, pre_roll: int = 8,
                 threshold_ratio: float = 3.5, min_threshold: float = 0.01,
                 threshold: float | None = None):
        self.calib_blocks = calib_blocks
        self.start_blocks = start_blocks
        self.end_blocks = end_blocks
        self.min_blocks = min_blocks
        self.max_blocks = max_blocks
        self.pre_roll = pre_roll
        self.threshold_ratio = threshold_ratio
        self.min_threshold = min_threshold
        self.threshold = threshold  # preset skips calibration (read-me windows)
        self._calib: list[float] = []
        self._recent: list = []       # pre-roll ring buffer of (block, rms)
        self._active: list = []       # blocks of the in-progress segment
        self._loud_run = 0
        self._quiet_run = 0
        self._in_speech = False

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

    def push(self, block):
        """Feed one audio block; returns a finished segment (list of blocks) or None."""
        rms = self._rms(block)

        if self.threshold is None:
            self._calib.append(rms)
            if len(self._calib) >= self.calib_blocks:
                floor = sum(self._calib) / len(self._calib)
                self.threshold = max(floor * self.threshold_ratio, self.min_threshold)
            return None

        loud = rms > self.threshold
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
        self._queue: queue.Queue = queue.Queue()
        self._awaiting_until = 0.0   # after a bare "Chirox", the next segment is the command
        self._threshold: float | None = None  # room noise floor, once calibrated
        self._panic = threading.Event()  # Ctrl+Alt+0: silence everything NOW
        self._chat: list[tuple[str, str]] = []  # this sitting's conversation turns
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

            self._voice = Voice()
        return self._voice

    # --- audio plumbing ---------------------------------------------------------

    def _block_frames(self) -> int:
        return int(self.SAMPLERATE * self.BLOCK_MS / 1000)

    def _callback(self, indata, frames, t, status):
        self._queue.put(indata[:, 0].copy())

    def _say(self, text: str) -> None:
        """Speak with the mic paused — Chirox must not hear himself."""
        print(f"[ear] chirox: {text}")
        if not self.speak_replies:
            return
        if self._stream is not None:
            self._stream.stop()
        try:
            self.voice.speak(text)
        except Exception as exc:  # keep listening even if the mouth fails
            print(f"[ear] (voice playback failed: {exc})")
        finally:
            if self._stream is not None:
                while not self._queue.empty():  # drop anything heard mid-speech
                    self._queue.get_nowait()
                self._stream.start()

    @property
    def narrator(self):
        if self._narrator is None:
            from chirox.narrator import Narrator

            self._narrator = Narrator()
        return self._narrator

    # --- read-me mode -------------------------------------------------------------

    def _drain_queue(self) -> None:
        while not self._queue.empty():
            self._queue.get_nowait()

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

    def _listen_window(self, seconds: float = 2.5, max_extra: float = 6.0) -> str:
        """Between passages: open the mic briefly; return a transcript or ''."""
        if self._stream is None:
            return ""
        self._drain_queue()
        self._stream.start()
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
            self._stream.stop()

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
        return self.voice.transcribe(wav, initial_prompt=WHISPER_PROMPT)

    # --- command handling ---------------------------------------------------------

    def _answer_day(self) -> str:
        from chirox.calendar import dojo_day

        d = dojo_day(self.config.practice_start_date)
        return d.headline()

    def _answer_master(self, question: str) -> str:
        """Normal conversation: one persona, spoken register, every exchange sealed."""
        from chirox.master.brain import MasterUnavailable, Ollama, converse, seal_exchange

        ok, reason = Ollama(self.config).available()
        if not ok:
            return f"The Master is silent — he will not fabricate. {reason}"
        try:
            answer = converse(self.config, question=question, history=self._chat)
        except MasterUnavailable as exc:
            return f"The Master is silent — he will not fabricate. {exc}"
        self._chat.append((question, answer))
        self._chat = self._chat[-4:]  # a sitting's worth of context, not a transcript
        try:
            seal_exchange(question, answer, self.config)
        except Exception as exc:  # logging must never silence the conversation
            print(f"[ear] (could not seal exchange: {exc})")
        return answer

    def handle_command(self, command: str) -> bool:
        """Execute one spoken command. Returns False when the ear should shut down."""
        kind = route(command)
        if kind == "sleep":
            self._say("Resting the ear. Train well.")
            return False
        if kind == "day":
            self._say(self._answer_day())
            return True
        if kind == "train":
            import subprocess
            import sys as _sys

            from chirox.config import REPO_ROOT

            self._say("Training call. Stand in front of the camera; I will call the drills.")
            flags = 0x08000000 if _sys.platform == "win32" else 0
            proc = subprocess.Popen([_sys.executable, "-m", "chirox.trainer"], cwd=str(REPO_ROOT),
                                    creationflags=flags, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            print(f"[ear] training session started (pid {proc.pid})")
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
        self._say(self._answer_master(command))
        return True

    def handle_transcript(self, text: str) -> bool:
        """Wake/command state machine over one transcript. Returns False to stop."""
        text = text.strip()
        if not text:
            return True
        woken, command = match_wake(text, self.aliases)

        # While a narration plays, the speakers are saying things like "Chirox" —
        # act only on a stop request, ignore everything else (it is mostly echo).
        from chirox.narrator import narration_pid, stop_narration

        if narration_pid() is not None:
            if stop_requested(_normalize(text), woken):
                stop_narration()
                self._say("Reading stopped.")
            else:
                print(f'[ear] (narration playing) "{text}"')
            return True

        if woken:
            print(f'[ear] wake word heard: "{text}"')
            if command:
                return self.handle_command(command)
            self._say("I am listening.")
            self._awaiting_until = time.monotonic() + 12.0
            return True
        if time.monotonic() < self._awaiting_until:
            self._awaiting_until = 0.0
            print(f'[ear] command: "{text}"')
            return self.handle_command(text)
        print(f'[ear] (not for me) "{text}"')
        return True

    # --- main loop ------------------------------------------------------------------

    def run(self, once: bool = False) -> None:
        import sounddevice as sd

        segmenter = SpeechSegmenter()
        self._stream = sd.InputStream(
            samplerate=self.SAMPLERATE, channels=1, dtype="float32",
            blocksize=self._block_frames(), device=self.device, callback=self._callback,
        )
        self.running = True
        try:
            import keyboard as kb

            kb.add_hotkey(PANIC_HOTKEY, self.panic)
            print(f"[ear] kill switch armed: {PANIC_HOTKEY} silences Chirox instantly")
        except Exception as exc:  # hotkey is a convenience, never a blocker
            print(f"[ear] (kill-switch hotkey unavailable: {exc})")
        print(f"[ear] awake — wake word: 'Chirox' (device: {self.device if self.device is not None else 'default'})")
        print("[ear] calibrating room noise (~1s of quiet, please)…")
        # Load the models before greeting so the first real exchange is not slow.
        _ = self.voice.whisper
        with self._stream:
            self._say("I am here.")
            try:
                while self.running:
                    block = self._queue.get()
                    segment = segmenter.push(block)
                    if segmenter.threshold is not None and segmenter._calib:
                        segmenter._calib = []
                        self._threshold = segmenter.threshold
                        print(f"[ear] noise floor set (threshold {segmenter.threshold:.4f}); listening.")
                    if segment is None:
                        continue
                    text = self._transcribe_segment(segment)
                    keep_going = self.handle_transcript(text)
                    if once and text.strip():
                        break
                    if not keep_going:
                        break
            except KeyboardInterrupt:
                print("\n[ear] interrupted — resting.")
        self.running = False


# --- self test (no microphone needed) ------------------------------------------------


def self_test() -> bool:
    """Prove the loop TTS→STT→wake→route with Chirox's own mouth as the speaker."""
    from chirox.voice import Voice

    v = Voice()
    phrase = "Chirox, what day is it today?"
    print(f'[self-test] speaking to a wav: "{phrase}"')
    wav = v.speak(phrase, play=False)
    heard = v.transcribe(wav, initial_prompt=WHISPER_PROMPT)
    print(f'[self-test] whisper heard:    "{heard}"')
    woken, command = match_wake(heard)
    kind = route(command) if woken else "-"
    print(f"[self-test] wake={woken} command={command!r} route={kind}")
    ok = woken and kind == "day"
    print(f"[self-test] {'PASS' if ok else 'FAIL'}")
    return ok


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Chirox always-on wake-word ear")
    ap.add_argument("--device", type=int, default=None, help="input device index (see --list-devices)")
    ap.add_argument("--list-devices", action="store_true", help="list audio devices and exit")
    ap.add_argument("--self-test", action="store_true", help="prove TTS→STT→wake routing without a mic")
    ap.add_argument("--once", action="store_true", help="handle one utterance then exit (mic check)")
    ap.add_argument("--no-speak", action="store_true", help="print replies instead of speaking them")
    args = ap.parse_args(argv)

    if args.list_devices:
        import sounddevice as sd

        print(sd.query_devices())
        return 0
    if args.self_test:
        return 0 if self_test() else 1

    ear = ChiroxEar(device=args.device, speak_replies=not args.no_speak)
    ear.run(once=args.once)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
