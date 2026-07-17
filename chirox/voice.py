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

import urllib.error
import urllib.request
import wave
from pathlib import Path

PIPER_VOICE = "en_GB-alan-medium"  # a calm British male voice, fitting for the Master
PIPER_DOWNLOAD_TIMEOUT_S = 120
PIPER_MIN_ONNX_BYTES = 100_000  # a real Piper voice is megabytes; refuse tiny garbage


class VoiceNotReady(RuntimeError):
    """Piper or Whisper is missing/broken — speak this honestly, never invent sound."""


def _piper_url_base(voice: str) -> str:
    """Derive the rhasspy/piper-voices URL for any '<locale>-<name>-<quality>' voice."""
    parts = voice.split("-")
    locale, quality, name = parts[0], parts[-1], "-".join(parts[1:-1])
    lang = locale.split("_")[0]
    return f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang}/{locale}/{name}/{quality}"


def _voice_dir() -> Path:
    from chirox.config import VOICE_DIR

    return VOICE_DIR


def _download_once(url: str, path: Path, *, timeout: float = PIPER_DOWNLOAD_TIMEOUT_S,
                   min_bytes: int = 1) -> None:
    """Fetch ``url`` to ``path`` atomically (temp + replace). Timeout + size check."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()
        if len(data) < min_bytes:
            raise VoiceNotReady(
                f"download of {path.name} was too small ({len(data)} bytes) — refusing to use it"
            )
        tmp.write_bytes(data)
        tmp.replace(path)
    except VoiceNotReady:
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise VoiceNotReady(f"could not download {path.name}: {exc}") from exc
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def ensure_piper(voice: str = PIPER_VOICE) -> tuple[Path, Path]:
    """Return (onnx, config) paths for the Piper voice, downloading once if absent.

    Downloads use a timeout and refuse truncated files. Failures raise
    ``VoiceNotReady`` so the ear can speak honesty instead of hanging forever.
    """
    d = _voice_dir()
    d.mkdir(parents=True, exist_ok=True)
    onnx, cfg = d / f"{voice}.onnx", d / f"{voice}.onnx.json"
    base = _piper_url_base(voice)
    for path, url, minimum in (
        (onnx, f"{base}/{voice}.onnx", PIPER_MIN_ONNX_BYTES),
        (cfg, f"{base}/{voice}.onnx.json", 20),
    ):
        if path.exists() and path.stat().st_size >= minimum:
            continue
        # ASCII only: Windows consoles default to cp1252 and choke on arrows
        print(f"Downloading Chirox's voice (once) -> {path.name} ...")
        _download_once(url, path, min_bytes=minimum)
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
                 whisper_device: str = "cpu", whisper_compute: str = "int8",
                 pace: float | None = None):
        self._piper_name = piper_voice
        self._whisper_name = whisper_model
        self._whisper_device = whisper_device
        self._whisper_compute = whisper_compute
        self.pace = pace  # Piper length_scale: >1.0 slows the cadence (a master does not rush)
        self._piper = None
        self._whisper = None

    @property
    def piper(self):
        if self._piper is None:
            from piper import PiperVoice

            try:
                onnx, cfg = ensure_piper(self._piper_name)
                self._piper = PiperVoice.load(str(onnx), config_path=str(cfg))
            except VoiceNotReady:
                raise
            except Exception as exc:
                raise VoiceNotReady(f"Piper voice could not load: {exc}") from exc
        return self._piper

    @property
    def whisper(self):
        if self._whisper is None:
            from faster_whisper import WhisperModel

            try:
                self._whisper = WhisperModel(self._whisper_name, device=self._whisper_device,
                                             compute_type=self._whisper_compute)
            except Exception as exc:
                raise VoiceNotReady(f"Whisper hearing could not load: {exc}") from exc
        return self._whisper

    def preflight(self) -> dict:
        """Honest readiness check for mouth and ears — no speech, no mic.

        Returns ``{ok, piper, whisper, error}``. Call this before the ear greets
        so a missing model becomes a spoken/printed truth, not a silent hang.
        """
        out: dict = {"ok": False, "piper": False, "whisper": False, "error": None}
        errors: list[str] = []
        try:
            _ = self.piper
            out["piper"] = True
        except Exception as exc:
            errors.append(str(exc))
        try:
            _ = self.whisper
            out["whisper"] = True
        except Exception as exc:
            errors.append(str(exc))
        out["ok"] = bool(out["piper"] and out["whisper"])
        out["error"] = "; ".join(errors) if errors else None
        return out

    # --- speak ---------------------------------------------------------------

    def speak(self, text: str, out_wav: Path | None = None, play: bool = True) -> Path:
        out = Path(out_wav) if out_wav else (_voice_dir() / "_last_spoken.wav")
        out.parent.mkdir(parents=True, exist_ok=True)
        spoken = speakable(text)
        if not spoken.strip():
            return out
        try:
            from chirox.activity import update_activity

            update_activity(last_spoken=spoken, piper_active=bool(play))
        except Exception:
            pass
        syn_config = None
        if self.pace is not None:
            from piper import SynthesisConfig

            syn_config = SynthesisConfig(length_scale=self.pace)
        try:
            with wave.open(str(out), "wb") as wf:
                self.piper.synthesize_wav(spoken, wf, syn_config=syn_config)
        except VoiceNotReady:
            try:
                from chirox.activity import update_activity

                update_activity(piper_active=False)
            except Exception:
                pass
            raise
        except Exception as exc:
            try:
                from chirox.activity import update_activity

                update_activity(piper_active=False)
            except Exception:
                pass
            raise VoiceNotReady(f"Piper could not speak: {exc}") from exc
        if play:
            self._play(out)
            try:
                from chirox.activity import update_activity

                update_activity(piper_active=False)
            except Exception:
                pass
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

    # Whisper's own no-speech decision rule: a segment is a hallucination (the
    # "Thank you." it invents over near-silence) only when BOTH signals agree —
    # high no-speech probability AND low decoding confidence.
    NO_SPEECH_PROB = 0.6
    LOW_LOGPROB = -1.0

    def _is_hallucinated(self, segment) -> bool:
        no_speech = getattr(segment, "no_speech_prob", 0.0) or 0.0
        logprob = getattr(segment, "avg_logprob", 0.0) or 0.0
        return no_speech > self.NO_SPEECH_PROB and logprob < self.LOW_LOGPROB

    def transcribe(self, wav: Path, initial_prompt: str | None = None) -> str:
        """Transcribe a local WAV. Live ear keeps ``initial_prompt=None`` so Whisper
        does not invent the wake word from room noise; self-test may pass a prompt.
        Segments Whisper marks as probable non-speech are discarded."""
        try:
            segments, _info = self.whisper.transcribe(
                str(wav),
                initial_prompt=initial_prompt,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 400},
            )
        except TypeError:
            # older faster-whisper without vad_filter kwargs
            segments, _info = self.whisper.transcribe(str(wav), initial_prompt=initial_prompt)
        except VoiceNotReady:
            raise
        except Exception as exc:
            raise VoiceNotReady(f"Whisper could not hear: {exc}") from exc
        return " ".join(s.text for s in segments if not self._is_hallucinated(s)).strip()

    def listen(self, seconds: float = 6.0, samplerate: int = 16000) -> str:
        import sounddevice as sd
        import soundfile as sf

        try:
            rec = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1)
            sd.wait()
        except Exception as exc:
            raise VoiceNotReady(f"microphone capture failed: {exc}") from exc
        tmp = _voice_dir() / "_last_heard.wav"
        sf.write(str(tmp), rec, samplerate)
        return self.transcribe(tmp)


def round_trip(text: str = "The first victory is showing up tomorrow.") -> str:
    """Speak text to a wav and transcribe it back — proves TTS+STT with no mic."""
    v = Voice()
    return v.transcribe(v.speak(text, play=False))
