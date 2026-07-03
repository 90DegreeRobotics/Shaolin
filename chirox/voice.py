"""Chirox's voice — local, sovereign speech. One being, now able to speak and hear.

- Text → speech via **Piper** (offline neural TTS; a calm voice for the Master).
- Speech → text via **faster-whisper** (offline STT).

Both run locally after a one-time model download; nothing leaves the machine. This
is the Charter's sovereignty applied to the senses: Chirox can talk with you during
training without renting its ears or its mouth from anyone.

Models and playback are imported lazily so the rest of the package stays importable
on machines without audio hardware.
"""

from __future__ import annotations

import urllib.request
import wave
from pathlib import Path

PIPER_VOICE = "en_GB-alan-medium"  # a calm British male voice, fitting for the Master


def _piper_url_base(voice: str) -> str:
    """Derive the rhasspy/piper-voices URL for any '<locale>-<name>-<quality>' voice."""
    parts = voice.split("-")
    locale, quality, name = parts[0], parts[-1], "-".join(parts[1:-1])
    lang = locale.split("_")[0]
    return f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang}/{locale}/{name}/{quality}"


def _voice_dir() -> Path:
    from chirox.config import VOICE_DIR

    return VOICE_DIR


def ensure_piper(voice: str = PIPER_VOICE) -> tuple[Path, Path]:
    """Return (onnx, config) paths for the Piper voice, downloading once if absent."""
    d = _voice_dir()
    d.mkdir(parents=True, exist_ok=True)
    onnx, cfg = d / f"{voice}.onnx", d / f"{voice}.onnx.json"
    base = _piper_url_base(voice)
    for path, url in ((onnx, f"{base}/{voice}.onnx"), (cfg, f"{base}/{voice}.onnx.json")):
        if not path.exists():
            # ASCII only: Windows consoles default to cp1252 and choke on arrows
            print(f"Downloading Chirox's voice (once) -> {path.name} ...")
            urllib.request.urlretrieve(url, path)
    return onnx, cfg


def speakable(text: str) -> str:
    """No symbol is ever voiced by name — not "asterisk", not "colon", nothing.

    Every speech path passes through here. Decoration characters vanish;
    structural punctuation becomes a silent pause (colon/semicolon → comma,
    except inside times like 10:30); "&" is spoken as the word it means.
    Words, numbers, and sentence punctuation pass untouched.
    """
    import re

    out: list[str] = []
    for i, c in enumerate(text):
        if c in "*#_`~|<>{}[]\\^=@$+":
            out.append(" ")
        elif c in ":;":
            prev = text[i - 1] if i else ""
            nxt = text[i + 1] if i + 1 < len(text) else ""
            out.append(c if (prev.isdigit() and nxt.isdigit()) else ",")
        elif c == "&":
            out.append(" and ")
        elif c == "/":
            prev = text[i - 1] if i else ""
            nxt = text[i + 1] if i + 1 < len(text) else ""
            out.append(c if (prev.isdigit() and nxt.isdigit()) else " ")
        else:
            out.append(c)
    cleaned = " ".join("".join(out).split())
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)   # no orphaned punctuation
    cleaned = re.sub(r",(\s*[,.])+", ",", cleaned)        # no stuttering pauses
    return cleaned


class Voice:
    def __init__(self, piper_voice: str = PIPER_VOICE, whisper_model: str = "base.en",
                 whisper_device: str = "cpu", whisper_compute: str = "int8"):
        self._piper_name = piper_voice
        self._whisper_name = whisper_model
        self._whisper_device = whisper_device
        self._whisper_compute = whisper_compute
        self._piper = None
        self._whisper = None

    @property
    def piper(self):
        if self._piper is None:
            from piper import PiperVoice

            onnx, cfg = ensure_piper(self._piper_name)
            self._piper = PiperVoice.load(str(onnx), config_path=str(cfg))
        return self._piper

    @property
    def whisper(self):
        if self._whisper is None:
            from faster_whisper import WhisperModel

            self._whisper = WhisperModel(self._whisper_name, device=self._whisper_device,
                                         compute_type=self._whisper_compute)
        return self._whisper

    # --- speak ---------------------------------------------------------------

    def speak(self, text: str, out_wav: Path | None = None, play: bool = True) -> Path:
        out = Path(out_wav) if out_wav else (_voice_dir() / "_last_spoken.wav")
        out.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out), "wb") as wf:
            self.piper.synthesize_wav(speakable(text), wf)
        if play:
            self._play(out)
        return out

    @staticmethod
    def _play(wav: Path) -> None:
        try:
            import sounddevice as sd
            import soundfile as sf

            data, sr = sf.read(str(wav))
            sd.play(data, sr)
            sd.wait()
        except Exception as exc:  # no audio device (e.g. headless) — fail soft
            print(f"(voice playback unavailable: {exc})")

    # --- hear ----------------------------------------------------------------

    def transcribe(self, wav: Path, initial_prompt: str | None = None) -> str:
        """``initial_prompt`` biases Whisper toward expected vocabulary — the ear
        passes the name "Chirox" so the wake word is not dropped as an unknown."""
        segments, _info = self.whisper.transcribe(str(wav), initial_prompt=initial_prompt)
        return " ".join(s.text for s in segments).strip()

    def listen(self, seconds: float = 6.0, samplerate: int = 16000) -> str:
        import sounddevice as sd
        import soundfile as sf

        rec = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1)
        sd.wait()
        tmp = _voice_dir() / "_last_heard.wav"
        sf.write(str(tmp), rec, samplerate)
        return self.transcribe(tmp)


def round_trip(text: str = "The first victory is showing up tomorrow.") -> str:
    """Speak text to a wav and transcribe it back — proves TTS+STT with no mic."""
    v = Voice()
    return v.transcribe(v.speak(text, play=False))
