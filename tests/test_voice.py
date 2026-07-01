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
