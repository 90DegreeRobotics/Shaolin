"""Voice is local and sovereign. Offline checks; the full TTS→STT round-trip is
verified live (it needs the Whisper model), not in the unit suite."""

import pytest

from chirox import voice


def test_ensure_piper_returns_existing_without_download(tmp_path, monkeypatch):
    onnx = tmp_path / "v.onnx"
    onnx.write_bytes(b"model")
    cfg = tmp_path / "v.onnx.json"
    cfg.write_bytes(b"{}")
    monkeypatch.setattr(voice, "_voice_dir", lambda: tmp_path)
    got_onnx, got_cfg = voice.ensure_piper("v")
    assert got_onnx == onnx and got_cfg == cfg


def test_speak_produces_a_wav_if_voice_present(tmp_path):
    from chirox.config import VOICE_DIR

    if not (VOICE_DIR / f"{voice.PIPER_VOICE}.onnx").exists():
        pytest.skip("piper voice model not downloaded in this environment")
    out = voice.Voice().speak("Return to the breath.", out_wav=tmp_path / "o.wav", play=False)
    assert out.exists() and out.stat().st_size > 1000


def test_measured_pace_slows_the_master(tmp_path):
    from chirox.config import VOICE_DIR

    if not (VOICE_DIR / f"{voice.PIPER_VOICE}.onnx").exists():
        pytest.skip("piper voice model not downloaded in this environment")
    text = "The path is walked, not discussed."
    quick = voice.Voice().speak(text, out_wav=tmp_path / "q.wav", play=False)
    slow = voice.Voice(pace=1.3).speak(text, out_wav=tmp_path / "s.wav", play=False)
    assert slow.stat().st_size > quick.stat().st_size  # more samples = slower speech


# --- STT hallucination filter (no model needed — Whisper is faked) -----------------


class _Seg:
    def __init__(self, text, no_speech_prob=0.0, avg_logprob=-0.2):
        self.text = text
        self.no_speech_prob = no_speech_prob
        self.avg_logprob = avg_logprob


class _FakeWhisper:
    def __init__(self, segments):
        self._segments = segments

    def transcribe(self, wav, initial_prompt=None):
        return iter(self._segments), None


def _voice_with(segments):
    v = voice.Voice()
    v._whisper = _FakeWhisper(segments)
    return v


def test_transcribe_keeps_confident_speech(tmp_path):
    v = _voice_with([_Seg(" Chirox,"), _Seg(" what day is it?")])
    assert v.transcribe(tmp_path / "x.wav") == "Chirox,  what day is it?"


def test_transcribe_drops_whisper_hallucinations(tmp_path):
    # the classic: near-silence transcribed as a polite phrase, both signals agreeing
    v = _voice_with([_Seg(" Thank you.", no_speech_prob=0.95, avg_logprob=-1.4)])
    assert v.transcribe(tmp_path / "x.wav") == ""


def test_transcribe_keeps_segment_when_only_one_signal_fires(tmp_path):
    # quiet-but-confident speech must NOT be discarded (soft real commands)
    v = _voice_with([_Seg(" go to sleep", no_speech_prob=0.9, avg_logprob=-0.3)])
    assert v.transcribe(tmp_path / "x.wav") == "go to sleep"
    v = _voice_with([_Seg(" mumbled words", no_speech_prob=0.2, avg_logprob=-1.8)])
    assert v.transcribe(tmp_path / "x.wav") == "mumbled words"
