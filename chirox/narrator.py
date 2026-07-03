"""Chirox the narrator — long-form reading aloud, audiobook style.

The Master's mouth (``voice.py``) is built for short spoken replies: it renders
one WAV and plays it. Reading a whole manual that way would mean minutes of
silence before the first word. The narrator instead:

1. cleans markdown into speakable prose (code blocks skipped, headers become
   sentences, links read as their text),
2. chunks the text at sentence and paragraph boundaries,
3. synthesizes the *next* chunk while the current one plays — so narration of
   any length starts within seconds and runs on a laptop's worth of memory.

The narrator voice is separate from the Master's: ``en_US-ryan-high``, a deep,
even, audiobook-grade Piper voice, paced slightly slower than conversation.
Everything is local — the voice model is fetched once and kept.

A running narration writes a PID lock so the ear can control it by voice:
"Chirox, read the manual" starts one; "Chirox, stop" ends it. While narration
plays, the ear ignores everything except stop requests — otherwise it would
wake itself every time the narrator speaks the word "Chirox".

Run it:   chirox narrate 1yeartoShaolin.md
          chirox narrate --text "..." | --out reading.wav | --from 12
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

# One being, one voice: the narrator speaks with the Master's voice (Chirox has
# no second self). Pace 1.0 — alan's natural cadence is already calm.
from chirox.voice import PIPER_VOICE as NARRATOR_VOICE

DEFAULT_PACE = 1.0
CHUNK_TARGET = 700    # characters per spoken chunk; ends on sentence boundaries


# --- text preparation (pure, testable) ----------------------------------------------


def clean_markdown(text: str) -> str:
    """Markdown → speakable prose. Code and images are dropped, structure becomes
    punctuation. Deterministic and lossless about actual sentences."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)            # fenced code: not prose
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)              # images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)         # links → their text
    text = text.replace("`", "")

    lines: list[str] = []
    for raw in text.splitlines():
        s = raw.strip()
        if s and re.fullmatch(r"[-*_=\s|:]{3,}", s):              # hrules, table separators
            continue
        if s.startswith("#"):
            s = s.lstrip("#").strip()
            if s and s[-1] not in ".!?:":
                s += "."
        s = re.sub(r"^>\s?", "", s)                               # blockquote marker
        s = re.sub(r"^[-*+]\s+", "", s)                           # bullet marker
        if s.startswith("|"):
            s = ", ".join(c.strip() for c in s.strip("|").split("|") if c.strip())
            if s and s[-1] not in ".!?":
                s += "."
        s = s.replace("**", "").replace("*", "")
        lines.append(s)

    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def chunk_text(text: str, target: int = CHUNK_TARGET) -> list[str]:
    """Split prose into narration chunks: sentences grouped up to ~``target``
    characters, never crossing a paragraph boundary (a natural breath)."""
    chunks: list[str] = []
    buf = ""

    def flush():
        nonlocal buf
        if buf.strip():
            chunks.append(buf.strip())
        buf = ""

    for para in text.split("\n\n"):
        para = " ".join(para.split())
        if not para:
            continue
        for s in re.split(r"(?<=[.!?])\s+", para):
            while len(s) > 2 * target:                 # a pathological unpunctuated run
                cut = s.rfind(" ", 0, target)
                if cut <= 0:
                    cut = target
                flush()
                chunks.append(s[:cut].strip())
                s = s[cut:].strip()
            if buf and len(buf) + len(s) + 1 > target:
                flush()
            buf = (buf + " " + s).strip()
        flush()                                        # paragraph = chunk boundary
    return chunks


# --- readable documents (for voice control) -------------------------------------------


def readable_docs() -> dict[str, tuple[str, Path]]:
    """Spoken keyword → (label, path) for docs the ear may be asked to read."""
    from chirox.config import DIET_DOC, MANUAL_PATH, REPO_ROOT

    dummies = REPO_ROOT / "Shaolin_For_Dummies.md"
    return {
        "manual": ("the manual", MANUAL_PATH),
        "book": ("the manual", MANUAL_PATH),
        "guide": ("the beginner guide", dummies),
        "dummies": ("the beginner guide", dummies),
        "status": ("the status report", REPO_ROOT / "STATUS.md"),
        "diet": ("the diet lane", DIET_DOC),
        "readme": ("the readme", REPO_ROOT / "README.md"),
    }


def resolve_doc(command: str) -> tuple[str, Path] | None:
    words = set(re.sub(r"[^a-z0-9\s]", " ", command.lower()).split())
    for key, (label, path) in readable_docs().items():
        if key in words and path.exists():
            return label, path
    return None


# --- the reading library (books + docs, resolvable by spoken name) --------------------

_TITLE_STOPWORDS = {"the", "of", "and", "a", "an", "literature", "chinese"}


def title_keys(title: str) -> set[str]:
    """Meaningful spoken words of a book title — what a wake command must hit."""
    words = re.sub(r"[^a-z0-9\s]", " ", title.lower()).split()
    return {w for w in words if w not in _TITLE_STOPWORDS and len(w) > 1}


def readable_catalog() -> list[tuple[str, set[str], Path]]:
    """Everything Chirox can be asked to read: (label, spoken keys, path).

    Docs come from ``readable_docs``; books come from the wisdom corpus that is
    actually present on disk — never a title we do not hold.
    """
    from chirox.config import WISDOM_DIR
    from chirox.wisdom import CORPUS

    catalog: list[tuple[str, set[str], Path]] = []
    seen_docs: dict[Path, tuple[str, set[str]]] = {}
    for key, (label, path) in readable_docs().items():
        if path.exists():
            if path in seen_docs:
                seen_docs[path][1].add(key)  # one entry per file, all its spoken names
            else:
                seen_docs[path] = (label, {key})
    catalog.extend((label, keys, path) for path, (label, keys) in seen_docs.items())
    for fn, (title, _url) in CORPUS.items():
        p = WISDOM_DIR / fn
        if p.exists():
            catalog.append((title, title_keys(title), p))
    return catalog


def match_readable(command: str, catalog: list[tuple[str, set[str], Path]]):
    """Best (label, path) for a spoken command, scored by title-word overlap.

    Space-insensitive fallback catches Whisper splits like "dhamma pada". Pure —
    testable with a synthetic catalog.
    """
    # Command words are noise for title matching — and "read me" squashes to
    # "readme", which would falsely hit the readme doc on every request.
    _command_words = {"read", "me", "the", "please", "chirox", "from", "beginning", "start", "over"}
    norm = re.sub(r"[^a-z0-9\s]", " ", command.lower())
    kept = [w for w in norm.split() if w not in _command_words]
    words = set(kept)
    squashed = "".join(kept)
    best, best_score = None, 0
    for label, keys, path in catalog:
        score = len(words & keys) + sum(1 for k in keys if k not in words and k in squashed)
        if score > best_score:
            best, best_score = (label, path), score
    return best


def resolve_readable(command: str) -> tuple[str, Path] | None:
    return match_readable(command, readable_catalog())


# --- reading progress (bookmarks per book) ---------------------------------------------


def _progress_path() -> Path:
    from chirox.config import DATA_DIR

    return DATA_DIR / "reading_progress.json"


def reading_progress(path: Path | None = None) -> dict:
    import json

    p = path or _progress_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def set_reading_progress(key: str, chunk_index: int, path: Path | None = None) -> None:
    import json

    p = path or _progress_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = reading_progress(p)
    if chunk_index <= 0:
        data.pop(key, None)
    else:
        data[key] = chunk_index
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# --- narration process lock (so the ear can stop a reading) ---------------------------


def _lock_path() -> Path:
    from chirox.config import VOICE_DIR

    return VOICE_DIR / "_narration.pid"


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        k = ctypes.windll.kernel32
        h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            k.GetExitCodeProcess(h, ctypes.byref(code))
            return code.value == 259  # STILL_ACTIVE
        finally:
            k.CloseHandle(h)
    try:
        import os

        os.kill(pid, 0)
        return True
    except OSError:
        return False


def narration_pid() -> int | None:
    """PID of a live narration, or None (stale locks self-heal)."""
    p = _lock_path()
    if not p.exists():
        return None
    try:
        pid = int(p.read_text().strip())
    except ValueError:
        p.unlink(missing_ok=True)
        return None
    if _pid_alive(pid):
        return pid
    p.unlink(missing_ok=True)
    return None


def stop_narration() -> bool:
    pid = narration_pid()
    if pid is None:
        return False
    if sys.platform == "win32":
        import ctypes

        PROCESS_TERMINATE = 0x0001
        k = ctypes.windll.kernel32
        h = k.OpenProcess(PROCESS_TERMINATE, False, pid)
        if h:
            k.TerminateProcess(h, 0)
            k.CloseHandle(h)
    else:
        import os
        import signal

        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    _lock_path().unlink(missing_ok=True)
    return True


def spawn_narration(path: Path, voice: str | None = None) -> int:
    """Start a narration as its own process (so the ear keeps listening)."""
    import subprocess

    from chirox.config import REPO_ROOT

    args = [sys.executable, "-m", "chirox.narrator", str(path)]
    if voice:
        args += ["--voice", voice]
    flags = 0x08000000 if sys.platform == "win32" else 0  # CREATE_NO_WINDOW
    proc = subprocess.Popen(args, cwd=str(REPO_ROOT), creationflags=flags,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc.pid


# --- the narrator ----------------------------------------------------------------------


class Narrator:
    def __init__(self, voice: str = NARRATOR_VOICE, pace: float = DEFAULT_PACE):
        self.voice_name = voice
        self.pace = pace
        self._piper = None

    @property
    def piper(self):
        if self._piper is None:
            from piper import PiperVoice

            from chirox.voice import ensure_piper

            onnx, cfg = ensure_piper(self.voice_name)
            self._piper = PiperVoice.load(str(onnx), config_path=str(cfg))
        return self._piper

    @property
    def samplerate(self) -> int:
        return self.piper.config.sample_rate

    def _syn_config(self):
        from piper import SynthesisConfig

        return SynthesisConfig(length_scale=self.pace)

    def synth(self, text: str):
        """One chunk of prose → one int16 numpy array."""
        import numpy as np

        from chirox.voice import speakable

        parts = [c.audio_int16_array for c in self.piper.synthesize(speakable(text), self._syn_config())]
        return np.concatenate(parts) if parts else np.zeros(0, dtype="int16")

    def read_aloud(self, chunks: list[str], start: int = 0) -> None:
        """Play chunks in order, synthesizing one chunk ahead of playback."""
        import queue
        import threading

        import sounddevice as sd

        q: queue.Queue = queue.Queue(maxsize=2)
        cancel = threading.Event()

        def produce():
            for i in range(start, len(chunks)):
                if cancel.is_set():
                    break
                q.put((i, self.synth(chunks[i])))
            q.put(None)

        lock = _lock_path()
        lock.parent.mkdir(parents=True, exist_ok=True)
        import os

        lock.write_text(str(os.getpid()), encoding="utf-8")
        try:
            import keyboard as kb

            kb.add_hotkey("ctrl+alt+0", lambda: (cancel.set(), sd.stop()))
        except Exception:
            pass  # hotkey is a convenience; Ctrl+C still works
        import numpy as np

        i = start
        t0 = time.perf_counter()
        threading.Thread(target=produce, daemon=True).start()
        sr = self.samplerate
        breath = np.zeros(int(sr * 0.22), dtype="int16")  # a breath between chunks
        slice_frames = sr // 2                            # cancel checked every half second
        try:
            # One continuous output stream: no per-chunk device stop/start,
            # which is what made narration sound choppy.
            with sd.OutputStream(samplerate=sr, channels=1, dtype="int16") as out:
                while True:
                    item = q.get()
                    if item is None:
                        break
                    i, audio = item
                    preview = chunks[i][:64]
                    print(f"[narrate {i + 1}/{len(chunks)}] {preview}…")
                    audio = np.concatenate([audio, breath])
                    for off in range(0, len(audio), slice_frames):
                        if cancel.is_set():
                            print(f"[narrate] killed at chunk {i + 1}. Resume with:  --from {i + 1}")
                            return
                        block = audio[off:off + slice_frames]
                        out.write(block.reshape(-1, 1))
            print(f"[narrate] finished {len(chunks) - start} chunk(s) "
                  f"in {time.perf_counter() - t0:.0f}s.")
        except KeyboardInterrupt:
            cancel.set()
            sd.stop()
            print(f"\n[narrate] stopped at chunk {i + 1}. Resume with:  --from {i + 1}")
        finally:
            lock.unlink(missing_ok=True)

    def render(self, chunks: list[str], out_path: Path, start: int = 0) -> Path:
        """Render the whole reading to a single WAV (no playback)."""
        import wave

        out_path = Path(out_path)
        with wave.open(str(out_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            for i in range(start, len(chunks)):
                wf.writeframes(self.synth(chunks[i]).tobytes())
                print(f"[render {i + 1}/{len(chunks)}]")
        return out_path


def prepare(path: Path | None = None, text: str | None = None,
            target: int = CHUNK_TARGET) -> list[str]:
    """File or raw text → narration chunks. Markdown files get cleaned first."""
    if text is None:
        raw = Path(path).read_text(encoding="utf-8-sig", errors="ignore")
        if "PROJECT GUTENBERG" in raw[:2000].upper():
            from chirox.wisdom import _BOILER, _strip_gutenberg

            raw = _strip_gutenberg(raw)
            # Drop leading credits/frontmatter ("Produced by …") — the narrator
            # announces the title itself; it should open on the text proper.
            paras = re.split(r"\n\s*\n", raw)
            drop = 0
            for p in paras[:30]:
                flat = " ".join(p.split()).lower()
                heading_like = len(flat) < 60 and (not flat or flat[-1] not in ".!?")
                if not flat or heading_like or any(b in flat for b in _BOILER):
                    drop += 1
                else:
                    break
            raw = "\n\n".join(paras[drop:])
        if str(path).lower().endswith((".md", ".markdown")):
            raw = clean_markdown(raw)
        text = raw
    else:
        text = clean_markdown(text) if "```" in text or "#" in text else text
    return chunk_text(text, target=target)


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Chirox narrator — read long texts aloud")
    ap.add_argument("path", nargs="?", help="text or markdown file to read")
    ap.add_argument("--text", help="read this literal text instead of a file")
    ap.add_argument("--voice", default=NARRATOR_VOICE, help=f"Piper voice (default {NARRATOR_VOICE})")
    ap.add_argument("--pace", type=float, default=DEFAULT_PACE,
                    help="pacing: 1.0 conversational, higher is slower (default %(default)s)")
    ap.add_argument("--from", dest="start", type=int, default=1, metavar="N",
                    help="start at chunk N (as printed during a previous reading)")
    ap.add_argument("--out", help="render to a single WAV file instead of playing")
    args = ap.parse_args(argv)

    if not args.path and not args.text:
        ap.error("give a file to read, or --text")
    if args.path and not Path(args.path).exists():
        print(f"no such file: {args.path}", file=sys.stderr)
        return 2

    chunks = prepare(args.path, args.text)
    if not chunks:
        print("nothing speakable in that text.", file=sys.stderr)
        return 1
    start = max(0, args.start - 1)
    n = Narrator(voice=args.voice, pace=args.pace)
    print(f"[narrate] {len(chunks)} chunk(s), voice {args.voice}, pace {args.pace}")
    if args.out:
        out = n.render(chunks, Path(args.out), start=start)
        print(f"[narrate] wrote {out}")
    else:
        n.read_aloud(chunks, start=start)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
