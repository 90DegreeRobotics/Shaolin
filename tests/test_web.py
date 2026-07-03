from dataclasses import asdict

from fastapi.testclient import TestClient

from chirox.vision.multicam import CameraRegistry
from chirox.vision.stances import StanceReading
from chirox.web.app import app
from chirox.web.live import (
    LiveSessionManager, SessionConfig, known_cameras, pack_frame, serialize_reading, unpack_frame,
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
    # three camera boxes
    assert "frontCanvas" in text
    assert "sideCanvas" in text
    assert "extraCanvas" in text
    # the toggle row — one page runs everything, no terminal
    for toggle in ("mirrorBtn", "earBtn", "trainBtn", "readBtn",
                   "recordBtn", "masterBtn", "silenceButton"):
        assert toggle in text, toggle
    # no typing required anywhere
    assert 'type="text"' not in text
    # the browser must never show a stale cockpit after an update
    assert response.headers["cache-control"] == "no-cache, must-revalidate"


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


def test_pack_frame_round_trips_header_and_jpeg():
    meta = {"type": "frame", "role": "front", "state": "measured", "landmarks": []}
    jpeg = b"\xff\xd8\xff\xe0fake-jpeg-bytes\xff\xd9"
    blob = pack_frame(meta, jpeg)
    assert isinstance(blob, bytes)
    got_meta, got_jpeg = unpack_frame(blob)
    assert got_meta == meta
    assert got_jpeg == jpeg


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
