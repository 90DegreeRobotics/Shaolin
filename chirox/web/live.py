"""Live camera session manager for the Chirox web cockpit."""

from __future__ import annotations

import asyncio
import json
import struct
import time
from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any

from chirox.vision.multicam import CameraRegistry
from chirox.vision.pipeline import points_from_landmarks
from chirox.vision.stances import STANCES

POSE_INDEX = {
    11: "left_shoulder",
    12: "right_shoulder",
    13: "left_elbow",
    14: "right_elbow",
    15: "left_wrist",
    16: "right_wrist",
    23: "left_hip",
    24: "right_hip",
    25: "left_knee",
    26: "right_knee",
    27: "left_ankle",
    28: "right_ankle",
}


@dataclass(frozen=True)
class SessionConfig:
    source: int | str = 0
    stance: str = "horse"
    view_mode: str = "overlay"
    role: str = "front"


def known_cameras() -> list[dict[str, Any]]:
    """The cockpit's camera list, derived from the one rig registry."""
    return [
        {"source": cam.source, "role": cam.role, "label": cam.label}
        for cam in CameraRegistry.default_rig().cameras
    ]


def pack_frame(meta: dict[str, Any], jpeg: bytes) -> bytes:
    """One binary websocket message: 4-byte big-endian header length, then the
    JSON header, then the raw JPEG. Keeps frame metadata and pixels atomic
    without base64 inflating every frame by a third."""
    header = json.dumps(meta).encode("utf-8")
    return struct.pack(">I", len(header)) + header + jpeg


def unpack_frame(blob: bytes) -> tuple[dict[str, Any], bytes]:
    """Inverse of ``pack_frame`` (used by tests; the browser mirrors this)."""
    (header_len,) = struct.unpack_from(">I", blob, 0)
    meta = json.loads(blob[4:4 + header_len].decode("utf-8"))
    return meta, blob[4 + header_len:]


def serialize_reading(reading) -> dict[str, Any]:
    return asdict(reading)


def landmarks_payload(landmarks) -> list[dict[str, float | str]]:
    out = []
    for idx, name in POSE_INDEX.items():
        lm = landmarks[idx]
        out.append({
            "name": name,
            "x": round(float(lm.x), 5),
            "y": round(float(lm.y), 5),
            "visibility": round(float(lm.visibility), 5),
        })
    return out


def camera_health(source: int | str) -> dict[str, Any]:
    from chirox.vision.capture import open_capture

    try:
        cap = open_capture(source)
    except RuntimeError:
        return {"source": source, "opened": False, "read": False, "width": 0, "height": 0}
    read, frame = cap.read()
    width = 0
    height = 0
    if read and frame is not None:
        height, width = frame.shape[:2]
    cap.release()
    return {"source": source, "opened": True, "read": bool(read), "width": width, "height": height}


class LiveSession:
    def __init__(self, config: SessionConfig):
        if config.stance not in STANCES:
            raise ValueError(f"unknown stance '{config.stance}'")
        self.config = config
        self._stop = False
        self._cap = None
        self._tracker = None

    def stop(self) -> None:
        self._stop = True

    def close(self) -> None:
        self._stop = True
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        if self._tracker is not None:
            self._tracker.close()
            self._tracker = None

    async def frames(self):
        import cv2

        from chirox.vision.capture import open_capture
        from chirox.vision.tracker import PoseTracker

        try:
            self._cap = open_capture(self.config.source)
        except RuntimeError as exc:
            yield {"type": "error", "message": str(exc)}
            return
        self._tracker = PoseTracker()
        evaluator = STANCES[self.config.stance]
        t0 = time.perf_counter()
        frame_index = 0
        try:
            while not self._stop and self._cap.isOpened():
                ret, frame = self._cap.read()
                if not ret or frame is None:
                    yield {"type": "error", "message": "Camera frame read failed."}
                    break

                frame_index += 1
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                lm = self._tracker.detect(rgb, elapsed_ms)

                ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if not ok:
                    continue
                meta: dict[str, Any] = {
                    "type": "frame",
                    "role": self.config.role,
                    "source": str(self.config.source),
                    "timestamp_ms": elapsed_ms,
                    "frame_index": frame_index,
                    "landmarks": [],
                    "reading": None,
                    "state": "no_body",
                }

                if lm:
                    pts = points_from_landmarks(lm)
                    reading = evaluator(pts)
                    meta["landmarks"] = landmarks_payload(lm)
                    meta["reading"] = serialize_reading(reading)
                    meta["state"] = "uncertain" if reading.uncertain else "measured"

                yield pack_frame(meta, encoded.tobytes())
                await asyncio.sleep(0)
        finally:
            self.close()


class LiveSessionManager:
    def __init__(self):
        self._lock = Lock()
        self._sessions: dict[str, LiveSession] = {}
        self._configs: dict[str, SessionConfig] = {"front": SessionConfig(role="front")}

    @property
    def config(self) -> SessionConfig:
        return self._configs.get("front", SessionConfig(role="front"))

    def start(self, config: SessionConfig) -> dict[str, Any]:
        return self.start_role(config.role, config)

    def start_role(self, role: str, config: SessionConfig) -> dict[str, Any]:
        with self._lock:
            old = self._sessions.get(role)
            if old is not None:
                old.stop()
                old.close()
            if config.role != role:
                config = SessionConfig(
                    source=config.source,
                    stance=config.stance,
                    view_mode=config.view_mode,
                    role=role,
                )
            self._configs[role] = config
            self._sessions[role] = LiveSession(config)
            return {"active": True, "role": role, "config": asdict(config)}

    def start_dual(self, front: SessionConfig, side: SessionConfig) -> dict[str, Any]:
        started = [
            self.start_role("front", front),
            self.start_role("side", side),
        ]
        return {"active": True, "sessions": started}

    def stop(self) -> dict[str, Any]:
        return self.stop_role("front")

    def stop_role(self, role: str) -> dict[str, Any]:
        with self._lock:
            session = self._sessions.pop(role, None)
            if session is not None:
                session.stop()
                session.close()
        return {"active": False, "role": role}

    def stop_all(self) -> dict[str, Any]:
        with self._lock:
            sessions = list(self._sessions.items())
            self._sessions = {}
        for _, session in sessions:
            session.stop()
            session.close()
        return {"active": False}

    def active(self) -> bool:
        return bool(self._sessions)

    def active_roles(self) -> list[str]:
        return sorted(self._sessions)

    def active_sources(self) -> set[str]:
        """Sources currently held by a live session (cameras are exclusive on
        Windows, so health probes must not touch these)."""
        with self._lock:
            return {str(self._configs[role].source) for role in self._sessions if role in self._configs}

    def configs(self) -> dict[str, dict[str, Any]]:
        return {role: asdict(config) for role, config in sorted(self._configs.items())}

    def current(self, role: str = "front") -> LiveSession:
        with self._lock:
            if role not in self._sessions:
                config = self._configs.get(role, SessionConfig(role=role))
                self._sessions[role] = LiveSession(config)
            return self._sessions[role]

    def clear(self, session: LiveSession) -> None:
        with self._lock:
            for role, current in list(self._sessions.items()):
                if current is session:
                    self._sessions.pop(role, None)
