"""Tests for the always-on ear — pure logic only: no mic, no models, no audio."""

import numpy as np

from chirox.listener import (
    ChiroxEar, LiveExchangeWitness, SpeechSegmenter, match_wake, route,
)


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


def test_route_reflection_requests():
    for cmd in ["reflect on my progress", "let us look back", "how have I grown",
                "how far have i come this month"]:
        assert route(cmd) == "reflect", cmd


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


def test_segmenter_recalibrates_noise_floor_while_idle():
    seg = SpeechSegmenter(
        calib_blocks=10, start_blocks=3, end_blocks=5, min_blocks=8,
        recalib_quiet_blocks=20, recalib_every_blocks=25,
    )
    _feed(seg, _blocks(0.001, 10))  # initial calibration
    first = seg.threshold
    assert first is not None
    # Quiet room gets a bit louder (HVAC) — idle blocks should refresh the floor.
    _feed(seg, _blocks(0.004, 40))
    assert seg.threshold is not None
    assert seg.threshold > first
    assert seg._blocks_since_recalib < 25


def test_ear_queue_is_bounded():
    ear = ChiroxEar(speak_replies=False)
    assert ear._queue.maxsize == ChiroxEar.MAX_QUEUE_BLOCKS


def test_wake_aliases_cover_common_soft_mishears():
    for heard in ["Shirox, what day is it?", "Tyrox train me", "Chi rocks, reflect"]:
        woken, _ = match_wake(heard)
        assert woken, heard


# --- live-exchange witness (the Gate 2 artifact) -------------------------------------


def test_witness_no_wake_verdict_and_render(tmp_path):
    w = LiveExchangeWitness(device=1, whisper_model="base.en", samplerate=16000)
    w.record(heard="the tv is on in the other room", woken=False, note="not addressed")
    assert not w.woke and not w.answered
    assert "NO WAKE" in w.verdict()
    text = w.render()
    assert "Live Exchange Witness" in text
    assert "the tv is on" in text


def test_witness_records_a_passing_exchange(tmp_path):
    w = LiveExchangeWitness()
    w.record(heard="the weather is nice", woken=False, note="not addressed")
    w.record(heard="Chirox what day is it", woken=True, command="what day is it",
             route="day", answer="Day 18. Stabilize.", spoken=True)
    assert w.woke and w.answered
    assert "PASS" in w.verdict()
    path = w.write(tmp_path / "exchange.local.md")
    body = path.read_text(encoding="utf-8")
    assert "PASS" in body
    assert "Day 18. Stabilize." in body
    assert "route: day" in body


def test_witness_wake_without_answer_is_partial():
    w = LiveExchangeWitness()
    w.record(heard="Chirox", woken=True, note="bare wake — no command")
    assert w.woke and not w.answered
    assert "PARTIAL" in w.verdict()


# --- the ear's exchange handling (no audio: speak_replies=False) ---------------------


def test_handle_transcript_witnesses_the_day_exchange():
    ear = ChiroxEar(speak_replies=False)
    ear._witness = LiveExchangeWitness()
    keep_going = ear.handle_transcript("Chirox, what day is it?")
    assert keep_going is True
    assert ear._exchange_done is True
    last = ear._witness.entries[-1]
    assert last["woken"] is True
    assert last["route"] == "day"
    assert last["answer"].strip()           # the day headline actually rendered
    assert ear._witness.answered


def test_exchange_done_only_flips_on_a_real_address():
    ear = ChiroxEar(speak_replies=False)
    ear._witness = LiveExchangeWitness()
    # stray room noise must NOT count as the "one exchange" that ends --once
    assert ear.handle_transcript("the weather is nice today") is True
    assert ear._exchange_done is False
    assert ear._witness.entries[-1]["woken"] is False
    # an addressed command does
    ear.handle_transcript("Chirox, what day is it?")
    assert ear._exchange_done is True
