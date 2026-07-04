"""Tests for the always-on ear — pure logic only: no mic, no models, no audio."""

import numpy as np

from chirox.listener import SpeechSegmenter, match_wake, route


# --- wake word ---------------------------------------------------------------------


def test_wake_plain():
    woken, cmd = match_wake("Chirox, what day is it?")
    assert woken
    assert cmd == "what day is it"


def test_wake_whisper_spellings_stay_tight():
    for heard in ["Kairox, hello.", "Kai Rox how am I doing", "KYROX!", "chirocks, status"]:
        woken, _ = match_wake(heard)
        assert woken, heard


def test_wake_bare_name_gives_empty_command():
    woken, cmd = match_wake("Chirox.")
    assert woken
    assert cmd == ""


def test_no_wake_on_ordinary_speech():
    for heard in ["what time is it", "the chair rocks gently", "hello there",
                  "the sky rocks tonight", "kairos is a concept", ""]:
        woken, _ = match_wake(heard)
        assert not woken, heard


def test_wake_with_short_address_prefix():
    woken, cmd = match_wake("Hey Chirox tell me about horse stance")
    assert woken
    assert cmd == "tell me about horse stance"


def test_no_wake_mid_sentence_room_audio():
    woken, _ = match_wake("I was telling Chirox from the book summary")
    assert not woken


# --- routing -----------------------------------------------------------------------


def test_route_sleep_phrases():
    for cmd in ["go to sleep", "please stop listening", "Shut down.", "goodnight"]:
        assert route(cmd) == "sleep", cmd


def test_route_day_questions():
    for cmd in ["what day is it", "which day am I on", "where do I stand"]:
        assert route(cmd) == "day", cmd


def test_route_mode_switches():
    assert route("learning mode") == "mode_learning"
    assert route("study mode") == "mode_learning"
    assert route("training mode") == "mode_training"
    assert route("mirror mode") == "mode_training"


def test_route_everything_else_to_master():
    assert route("how deep should my horse stance be") == "master"


def test_route_read_known_doc():
    assert route("read the manual") == "read"
    assert route("read me the status report") == "read"


def test_route_read_without_known_doc_goes_to_master():
    assert route("what should i read next") == "master"


def test_stop_requested_during_narration():
    from chirox.listener import stop_requested

    assert stop_requested("stop", woken=False)                       # short bare stop
    assert stop_requested("stop reading", woken=False)
    assert stop_requested("please stop reading now thanks", woken=True)  # wake + stop
    # long echo of a document sentence containing 'stop' is NOT a request
    assert not stop_requested("the stop button releases the camera when pressed", woken=False)
    assert not stop_requested("keep going this is great", woken=True)


# --- energy segmenter ----------------------------------------------------------------


def _blocks(amplitude: float, n: int, frames: int = 480):
    return [np.full(frames, amplitude, dtype="float32") for _ in range(n)]


def _feed(seg, blocks):
    out = []
    for b in blocks:
        r = seg.push(b)
        if r is not None:
            out.append(r)
    return out


def test_segmenter_preset_threshold_skips_calibration():
    seg = SpeechSegmenter(threshold=0.01, start_blocks=2, end_blocks=5, min_blocks=4)
    got = _feed(seg, _blocks(0.2, 10) + _blocks(0.001, 10))  # immediate speech, no calib
    assert len(got) == 1


def test_segmenter_calibrates_then_stays_quiet_on_silence():
    seg = SpeechSegmenter(calib_blocks=10)
    got = _feed(seg, _blocks(0.001, 60))
    assert seg.threshold is not None
    assert got == []


def test_segmenter_captures_a_speech_burst():
    seg = SpeechSegmenter(calib_blocks=10, start_blocks=3, end_blocks=5, min_blocks=8)
    _feed(seg, _blocks(0.001, 10))                 # calibration on quiet room
    got = _feed(seg, _blocks(0.001, 5) + _blocks(0.2, 20) + _blocks(0.001, 10))
    assert len(got) == 1
    assert len(got[0]) >= 20  # burst plus pre-roll, minus nothing


def test_segmenter_ignores_a_click():
    # one loud block (a door click) never reaches start_blocks
    seg = SpeechSegmenter(calib_blocks=10, start_blocks=3, end_blocks=5)
    _feed(seg, _blocks(0.001, 10))
    got = _feed(seg, _blocks(0.001, 3) + _blocks(0.5, 1) + _blocks(0.001, 20))
    assert got == []


def test_segmenter_discards_too_short_segment():
    seg = SpeechSegmenter(calib_blocks=10, start_blocks=2, end_blocks=3, min_blocks=50)
    _feed(seg, _blocks(0.001, 10))
    got = _feed(seg, _blocks(0.2, 10) + _blocks(0.001, 10))
    assert got == []  # real burst, but shorter than min_blocks


def test_segmenter_caps_runaway_segment():
    seg = SpeechSegmenter(calib_blocks=10, start_blocks=2, end_blocks=5, min_blocks=8, max_blocks=30)
    _feed(seg, _blocks(0.001, 10))
    got = _feed(seg, _blocks(0.2, 100))  # someone left the TV on
    assert len(got) >= 1
    assert all(len(s) <= 30 for s in got)


def test_segmenter_reset_drops_in_progress_speech():
    seg = SpeechSegmenter(calib_blocks=10, start_blocks=2, end_blocks=5, min_blocks=4)
    _feed(seg, _blocks(0.001, 10))
    _feed(seg, _blocks(0.2, 6))  # speech has started…
    seg.reset()                  # …but Chirox began talking; drop it
    got = _feed(seg, _blocks(0.001, 10))
    assert got == []
