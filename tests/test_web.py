from dataclasses import asdict

from fastapi.testclient import TestClient

from chirox.vision.multicam import CameraRegistry
from chirox.vision.stances import StanceReading
from chirox.web.app import app
from chirox.web.live import (
    LiveSessionManager, SessionConfig, known_cameras, landmarks_payload, pack_frame,
    serialize_reading, unpack_frame,
)


def test_status_endpoint_shape():
    client = TestClient(app)
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert {"practice", "model", "camera_defaults", "pose_model", "codex", "session"} <= data.keys()
    assert data["camera_defaults"] == {"front": 0, "side": 2, "extra": 1}
    assert "active_roles" in data["session"]


def test_static_frontend_served():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    text = response.text
    # one built-in webcam mirror
    assert "frontCanvas" in text
    assert "sideCanvas" not in text
    assert "extraCanvas" not in text
    assert "Wireguy" in text or "practiceStage" in text
    assert "guideName" in text
    assert "guideImage" in text
    assert "learningDeck" in text
    assert "masterQuestion" in text
    assert "dailyForm" in text
    assert "mandarinForm" in text
    assert "learningBooks" in text
    # practice stage — Wireguy owns the first screen; ear stays in the top bar
    for element in ("practiceStage", "earBtn", "silenceButton", "trainBtn",
                   "recordBtn", "pickWorkBtn", "workDrawer", "WAKE", "CALL ME",
                   "routinesCard", "routineList", "hudPhase", "routineNextBtn",
                   "routineStopBtn", "practiceBar", "practice-cluster",
                   "autoDetectBtn", "Detecting"):
        assert element in text, element
    # Practice actions live in the top bar — nothing below the camera stage.
    assert text.index("practiceBar") < text.index("practiceStage")
    assert text.index("trainBtn") < text.index("frontCanvas")
    assert "practice-bar" not in text
    # Opens in auto-detect, not locked to horse.
    assert 'stance: "auto"' in client.get("/static/app.js").text
    # the Training Hall lives in Pick Work, with a fullscreen viewer
    for element in ("trainingHall", "hallGroups", "chartShelf",
                    "lightbox", "lbImage", "lbPlaybackTools"):
        assert element in text, element
    # recording is never a mystery: banner with STOP, archive with playback,
    # and the mirror says plainly that it saves nothing
    for element in ("recBanner", "recStopBtn", "recordingsCard", "recordingsList",
                    "openFolderBtn", "lbVideo", "trackedStance", "nothing is saved",
                    "hudAngles", "truthState"):
        assert element in text, element
    # the browser must never show a stale cockpit after an update
    assert response.headers["cache-control"] == "no-cache, must-revalidate"


def test_frontend_notifies_camera_loading_and_busts_asset_cache():
    import re

    client = TestClient(app)
    text = client.get("/").text
    # the mirror says the camera is opening instead of showing a blank stage
    assert "camLoading" in text
    assert "Waking the camera" in text
    # JS/CSS carry a cache-busting version query — the app runs in a persistent
    # Edge profile that would otherwise serve a stale cockpit after an update
    assert re.search(r"/static/app\.js\?v=\d+", text), "app.js must be version-busted"
    assert re.search(r"/static/styles\.css\?v=\d+", text), "styles.css must be version-busted"


def test_shipped_app_js_has_head_neck_and_camera_loading():
    client = TestClient(app)
    js = client.get("/static/app.js").text
    assert "drawHeadAndNeck" in js   # the wireguy tracks head and neck
    assert "showCamLoading" in js    # the camera-loading notification


def test_recordings_endpoint_lists_archive():
    client = TestClient(app)
    response = client.get("/api/recordings")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "folder" in data and "items" in data
    for item in data["items"]:
        assert {"file", "url", "play_url", "proxy_ready", "exercise", "size_mb", "sealed"} <= item.keys()
        assert item["url"].startswith("/media/")
        assert item["play_url"].startswith("/media/")


def test_open_recording_refuses_paths_outside_the_archive():
    from chirox.web.control import open_recording

    res = open_recording("../../Dojo/data/dojo_record.jsonl")
    assert res["ok"] is False


def test_playback_refuses_paths_outside_the_archive():
    from chirox.web.control import playback_recording, prepare_playback

    assert playback_recording("../../Dojo/data/dojo_record.jsonl")["ok"] is False
    assert prepare_playback("../../Dojo/data/dojo_record.jsonl")["ok"] is False


def test_playback_prefers_cached_browser_proxy(tmp_path, monkeypatch):
    import os

    from chirox import config
    from chirox.web import control

    monkeypatch.setattr(config, "MEDIA_DIR", tmp_path)
    clip = tmp_path / "horse_stance" / "clip.mp4"
    clip.parent.mkdir(parents=True)
    clip.write_bytes(b"original mp4")
    proxy = control._playback_proxy_path(clip)
    proxy.parent.mkdir(parents=True)
    proxy.write_bytes(b"browser mp4")
    newer = clip.stat().st_mtime + 10
    os.utime(proxy, (newer, newer))

    res = control.playback_recording("horse_stance/clip.mp4")
    assert res["ok"] is True
    assert res["proxy_ready"] is True
    assert "/media/_playback/" in res["url"]


def test_prepare_playback_offers_streaming_replay_without_ffmpeg(tmp_path, monkeypatch):
    from chirox import config
    from chirox.web import control

    monkeypatch.setattr(config, "MEDIA_DIR", tmp_path)
    monkeypatch.setattr(control.shutil, "which", lambda _name: None)
    clip = tmp_path / "free_training" / "clip.mp4"
    clip.parent.mkdir(parents=True)
    clip.write_bytes(b"original mp4")

    res = control.prepare_playback("free_training/clip.mp4")
    assert res["ok"] is False
    assert res["mjpeg_url"].startswith("/api/recordings/mjpeg?file=free_training%2Fclip.mp4")
    assert "streaming replay" in res["error"]


def test_recording_status_false_without_marker(tmp_path, monkeypatch):
    from chirox.web import control

    monkeypatch.setattr(control, "_recording_marker", lambda: tmp_path / "recording_status.json")
    assert control.recording_status() == {"recording": False}


def test_recording_status_ignores_dead_pid(tmp_path, monkeypatch):
    import json as _json

    from chirox.web import control

    marker = tmp_path / "recording_status.json"
    marker.write_text(_json.dumps({"exercise": "horse_stance", "pid": 99999999,
                                   "seconds": 60, "started": "2026-07-06T00:00:00+00:00"}),
                      encoding="utf-8")
    monkeypatch.setattr(control, "_recording_marker", lambda: marker)
    assert control.recording_status()["recording"] is False
    assert not marker.exists()  # a stale marker is cleaned up, not trusted


def test_routine_catalog_and_start_next_stop_without_seal():
    client = TestClient(app)
    catalog = client.get("/api/routine/catalog").json()
    assert any(r["key"] == "eight_brocades_ste" for r in catalog["routines"])
    started = client.post("/api/routine/start", json={"routine_key": "eight_brocades_ste"}).json()
    assert started.get("ok") is True
    assert started["phase_key"] == "bdj_open"
    nxt = client.post("/api/routine/next").json()
    assert nxt["phase_key"] == "bdj_support_heaven"
    stopped = client.post("/api/routine/stop", json={"seal": False}).json()
    assert stopped["ok"] is True
    assert stopped["sealed"] is False
    assert stopped["summary"]["totals"]["phases_completed"] >= 2
    assert client.get("/api/routine/status").json()["active"] is False


def test_guides_endpoint_serves_catalog_and_references():
    client = TestClient(app)
    response = client.get("/api/guides")
    assert response.status_code == 200
    data = response.json()
    assert {"references", "drills"} <= data.keys()
    horse = next(d for d in data["drills"] if d["key"] == "horse")
    assert horse["guide_kind"] == "stance"
    assert horse["instruction"]
    assert "webcam" in horse["camera_instruction"].lower()
    if data["references"]:
        assert data["references"][0]["url"].startswith("/reference/")


def test_every_drill_maps_to_its_own_chart():
    """No arbitrary poster assignment: each drill names a chart, the chart file
    exists, and the chart carries its real printed title."""
    from chirox.trainer import full_catalog
    from chirox.web.guides import CHART_TITLES, DRILL_CHARTS, drill_guides

    catalog_keys = {d["key"] for d in full_catalog()}
    assert catalog_keys == set(DRILL_CHARTS), (
        "every trainable drill needs an explicit chart mapping"
    )
    data = drill_guides()
    if not data["references"]:  # charts not present in this environment
        return
    numbers_on_disk = {r["number"] for r in data["references"]}
    for drill in data["drills"]:
        assert drill["guide_image"] is not None, drill["key"]
        expected = DRILL_CHARTS[drill["key"]]
        if expected in numbers_on_disk:
            assert drill["guide_image"]["number"] == expected, drill["key"]
            assert drill["guide_image"]["title"] == CHART_TITLES[expected]


def test_chart_titles_are_the_printed_poster_titles():
    from chirox.web.guides import CHART_TITLES, reference_images

    refs = reference_images()
    if not refs:
        return
    assert len(refs) == 10, "the full poster set, never a subset"
    titles = {r["title"] for r in refs}
    assert "Qi Gong" in titles
    assert "Balance" in titles
    assert "Floor Work + Beginner Daily Circuit" in titles
    assert not any(t.startswith("Reference ") for t in titles), (
        "charts carry their real names, not placeholder numbers"
    )
    assert set(CHART_TITLES) == set(range(1, 11))


def test_mode_endpoint_defaults_to_known_mode():
    client = TestClient(app)
    response = client.get("/api/mode")
    assert response.status_code == 200
    assert response.json()["mode"] in {"training", "learning"}


def test_learning_endpoint_shape():
    client = TestClient(app)
    response = client.get("/api/learning")
    assert response.status_code == 200
    data = response.json()
    assert {"activity", "library", "mandarin_focus", "days", "record"} <= data.keys()
    assert {"character", "pinyin", "meaning", "question"} <= data["mandarin_focus"].keys()
    assert data["library"]


def test_learning_day_endpoint_shape():
    client = TestClient(app)
    response = client.get("/api/learning/day/1")
    assert response.status_code == 200
    data = response.json()
    assert data["day_number"] == 1
    assert "daily" in data and "mandarin" in data
    assert data["mandarin_focus"]["character"] == "道"


def test_serialize_reading_preserves_truth_fields():
    reading = StanceReading(
        stance="Horse Stance (Ma Bu)",
        metrics={"left_knee_angle": 104.0},
        flags=["low_visibility"],
        assessment="UNCERTAIN",
        confidence=0.31,
        uncertain=True,
    )
    assert serialize_reading(reading) == asdict(reading)


def test_session_manager_replaces_active_session():
    manager = LiveSessionManager()
    first = manager.start(SessionConfig(source=0, stance="horse"))
    second = manager.start(SessionConfig(source=2, stance="bow"))
    assert first["active"] is True
    assert second["active"] is True
    assert second["config"]["source"] == 2
    assert second["config"]["stance"] == "bow"
    assert manager.stop() == {"active": False, "role": "front"}


def test_session_stop_is_idempotent():
    manager = LiveSessionManager()
    assert manager.stop() == {"active": False, "role": "front"}
    assert manager.stop() == {"active": False, "role": "front"}


def test_known_cameras_derive_from_the_rig_registry():
    rig = {c.role: c.source for c in CameraRegistry.default_rig().cameras}
    assert {cam["role"]: cam["source"] for cam in known_cameras()} == rig


def test_landmarks_payload_tracks_head_and_neck():
    # The cockpit wireframe must carry head points (nose + both ears) so the
    # mirror can draw a head and neck that follow the practitioner — plus the
    # shoulders the neck hangs from.
    class Lm:
        x = 0.4
        y = 0.3
        visibility = 0.9

    payload = landmarks_payload([Lm() for _ in range(33)])
    names = {p["name"] for p in payload}
    assert {"nose", "left_ear", "right_ear"} <= names
    assert {"left_shoulder", "right_shoulder"} <= names


def test_landmarks_payload_tracks_hands_and_feet():
    # The full-body wireguy carries every articulated joint — hands (thumb /
    # index / pinky) and feet (heel + toe), both sides — so nothing the
    # practitioner moves goes untracked.
    class Lm:
        x = 0.4
        y = 0.3
        visibility = 0.9

    names = {p["name"] for p in landmarks_payload([Lm() for _ in range(33)])}
    hands = {"left_thumb", "left_index", "left_pinky", "right_thumb", "right_index", "right_pinky"}
    feet = {"left_heel", "left_foot_index", "right_heel", "right_foot_index"}
    assert hands <= names
    assert feet <= names


def test_shipped_app_js_reads_head_yaw_and_pitch():
    client = TestClient(app)
    js = client.get("/static/app.js").text
    assert "drawHeadOrientation" in js
    assert "pitch" in js                 # up / down as well as left / right
    assert '"down"' in js or " down" in js
    assert '"up"' in js or " up" in js


def test_pack_frame_round_trips_header_and_jpeg():
    meta = {"type": "frame", "role": "front", "state": "measured", "landmarks": []}
    jpeg = b"\xff\xd8\xff\xe0fake-jpeg-bytes\xff\xd9"
    blob = pack_frame(meta, jpeg)
    assert isinstance(blob, bytes)
    got_meta, got_jpeg = unpack_frame(blob)
    assert got_meta == meta
    assert got_jpeg == jpeg


def test_session_config_defaults_to_auto_detect():
    cfg = SessionConfig()
    assert cfg.stance == "auto"
    manager = LiveSessionManager()
    started = manager.start(SessionConfig(source=0, stance="auto", role="front"))
    assert started["config"]["stance"] == "auto"
    manager.stop_all()


def test_session_manager_reports_active_sources():
    manager = LiveSessionManager()
    assert manager.active_sources() == set()
    manager.start_dual(
        SessionConfig(source=0, stance="horse", role="front"),
        SessionConfig(source=2, stance="horse", role="side"),
    )
    assert manager.active_sources() == {"0", "2"}
    manager.stop_all()
    assert manager.active_sources() == set()


def test_session_manager_starts_dual_roles():
    manager = LiveSessionManager()
    result = manager.start_dual(
        SessionConfig(source=0, stance="horse", role="front"),
        SessionConfig(source=2, stance="horse", role="side"),
    )
    assert result["active"] is True
    assert manager.active_roles() == ["front", "side"]
    assert manager.stop_all() == {"active": False}
