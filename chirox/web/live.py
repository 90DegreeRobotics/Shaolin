"""Live camera session manager for the Chirox web cockpit."""

from __future__ import annotations

import asyncio
import json
import os
import struct
import time
from dataclasses import asdict, dataclass
from threading import Lock
from typing import Any

from chirox.vision.multicam import CameraRegistry
from chirox.vision.pipeline import points_from_landmarks
from chirox.vision.stances import STANCES

# Cockpit singleton — control.py consults this for live-tee recording status
# without importing the FastAPI app (circular).
_COCKPIT_MANAGER: "LiveSessionManager | None" = None


def cockpit_manager() -> "LiveSessionManager | None":
    return _COCKPIT_MANAGER

# Landmarks the cockpit wireframe DRAWS: the full articulated skeleton. Head
# points (nose + both ears) let the mirror draw a head, a neck, and read head
# turn; the arms run down to the hands (thumb / index / pinky knuckles) and the
# legs down to the feet (heel + toe) so every joint the practitioner moves is
# tracked. All of it is overlay-only and never reaches the deterministic stance
# geometry, which keeps its own 12-joint map in
# ``vision/pipeline.points_from_landmarks``.
POSE_INDEX = {
    0: "nose",
    7: "left_ear",
    8: "right_ear",
    11: "left_shoulder",
    12: "right_shoulder",
    13: "left_elbow",
    14: "right_elbow",
    15: "left_wrist",
    16: "right_wrist",
    17: "left_pinky",
    18: "right_pinky",
    19: "left_index",
    20: "right_index",
    21: "left_thumb",
    22: "right_thumb",
    23: "left_hip",
    24: "right_hip",
    25: "left_knee",
    26: "right_knee",
    27: "left_ankle",
    28: "right_ankle",
    29: "left_heel",
    30: "right_heel",
    31: "left_foot_index",
    32: "right_foot_index",
}


# Live mirror default: watch first, name what is seen. Locked holds are opt-in.
AUTO_STANCE = "auto"


@dataclass(frozen=True)
class SessionConfig:
    source: int | str = 0
    stance: str = AUTO_STANCE
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
    def __init__(self, config: SessionConfig, manager: "LiveSessionManager | None" = None):
        if config.stance != AUTO_STANCE and config.stance not in STANCES:
            raise ValueError(f"unknown stance '{config.stance}'")
        self.config = config
        self._manager = manager
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
        t0 = time.perf_counter()
        frame_index = 0
        try:
            while not self._stop and self._cap.isOpened():
                ret, frame = self._cap.read()
                if not ret or frame is None:
                    yield {"type": "error", "message": "Camera frame read failed."}
                    break

                frame_index += 1
                elapsed_s = time.perf_counter() - t0
                elapsed_ms = int(elapsed_s * 1000)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                lm = self._tracker.detect(rgb, elapsed_ms)

                if self._manager is not None:
                    self._manager.tee_frame(frame, lm, elapsed_s)

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
                    "routine": None,
                    "free_tag": None,
                    "auto": self.config.stance == AUTO_STANCE,
                    "recording": bool(self._manager and self._manager.is_recording()),
                }

                if lm:
                    pts = points_from_landmarks(lm)
                    meta["landmarks"] = landmarks_payload(lm)
                    reading = None
                    if self._manager is not None:
                        meta["routine"] = self._manager.push_routine(pts, elapsed_s)
                    if self.config.stance == AUTO_STANCE:
                        from chirox.vision.sequences import detect_stance
                        from chirox.vision.stances import StanceReading

                        hit = detect_stance(pts)
                        if hit is not None:
                            reading = STANCES[hit["key"]](pts)
                            meta["free_tag"] = {
                                "key": hit["key"],
                                "label": hit["label"],
                                "confidence": hit["confidence"],
                                "flags": hit["flags"],
                                "form_clean": hit["form_clean"],
                            }
                        else:
                            # Body visible, no clear named hold yet — do not invent one.
                            vis = [float(getattr(lm[i], "visibility", 0)) for i in (11, 12, 23, 24)]
                            conf = sum(vis) / len(vis) if vis else 0.0
                            reading = StanceReading(
                                "Detecting",
                                {},
                                [],
                                "Watching for a known hold. Stand a shape, or pick one.",
                                round(conf, 3),
                                False,
                            )
                    else:
                        # Locked hold: re-read each frame so RECORD can switch
                        # without killing the camera / freezing Wireguy.
                        reading = STANCES[self.config.stance](pts)
                        if self._manager is not None and meta["routine"] is None:
                            meta["free_tag"] = self._manager.free_tag(pts)
                    meta["reading"] = serialize_reading(reading)
                    meta["state"] = "uncertain" if reading.uncertain else "measured"

                yield pack_frame(meta, encoded.tobytes())
                await asyncio.sleep(0)
        finally:
            self.close()


class LiveSessionManager:
    def __init__(self):
        global _COCKPIT_MANAGER
        self._lock = Lock()
        self._sessions: dict[str, LiveSession] = {}
        self._configs: dict[str, SessionConfig] = {"front": SessionConfig(role="front")}
        self._routine = None  # SequenceTracker | None
        self._routine_t0 = 0.0
        self._tee = None  # LiveTeeRecorder | None
        self._tee_started: str | None = None
        _COCKPIT_MANAGER = self

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
            self._sessions[role] = LiveSession(config, manager=self)
            return {"active": True, "role": role, "config": asdict(config)}

    # --- named routines (Eight Brocades etc.) --------------------------------

    def start_routine(self, routine_key: str) -> dict[str, Any]:
        from chirox.vision.sequences import make_tracker

        with self._lock:
            self._routine = make_tracker(routine_key)
            self._routine_t0 = time.perf_counter()
            return {"ok": True, **self._routine.status()}

    def next_routine_phase(self) -> dict[str, Any]:
        with self._lock:
            if self._routine is None:
                return {"ok": False, "error": "no routine active"}
            t = time.perf_counter() - self._routine_t0
            return {"ok": True, **self._routine.next_phase(t)}

    def stop_routine(self, seal: bool = True, source: str = "0") -> dict[str, Any]:
        from chirox.vision.sequences import seal_routine_session

        with self._lock:
            if self._routine is None:
                return {"ok": False, "error": "no routine active"}
            t = time.perf_counter() - self._routine_t0
            summary = self._routine.stop(t)
            self._routine = None
        if seal:
            sealed = seal_routine_session(summary, source=source)
            return {"ok": True, "sealed": True, "summary": summary, "event": sealed}
        return {"ok": True, "sealed": False, "summary": summary}

    def routine_status(self) -> dict[str, Any]:
        with self._lock:
            if self._routine is None:
                return {"active": False}
            return {"active": True, **self._routine.status()}

    def push_routine(self, points, elapsed_s: float) -> dict[str, Any] | None:
        with self._lock:
            if self._routine is None:
                return None
            return self._routine.push(points, elapsed_s)

    def free_tag(self, points) -> dict[str, Any] | None:
        if self._routine is not None:
            return None
        from chirox.vision.sequences import free_train_tag

        return free_train_tag(points)

    # --- live-tee recording (camera stays with Wireguy) ----------------------

    def is_recording(self) -> bool:
        with self._lock:
            return self._tee is not None and not self._tee.finished

    def recording_info(self) -> dict[str, Any]:
        with self._lock:
            if self._tee is None or self._tee.finished:
                return {"recording": False}
            info = self._tee.info()
            info["started"] = self._tee_started
            info["pid"] = os.getpid()
            return info

    def begin_recording(self, exercise: str, source: str | int, seconds: int,
                        stance: str | None = None) -> dict[str, Any]:
        """Attach a file writer to the live mirror — do not steal the camera."""
        from datetime import datetime, timezone

        from chirox.vision.recorder import LiveTeeRecorder

        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in exercise.strip().lower())
        if not safe:
            return {"ok": False, "error": "exercise name is required"}
        try:
            src: int | str = int(source) if str(source).isdigit() else source
        except (TypeError, ValueError):
            src = source
        stance_key = stance if stance in STANCES else None
        with self._lock:
            if self._tee is not None and not self._tee.finished:
                return {"ok": False, "error": "already recording"}
            try:
                self._tee = LiveTeeRecorder(safe, src, float(seconds) if seconds else None, stance_key)
            except ValueError as exc:
                return {"ok": False, "error": str(exc)}
            self._tee_started = datetime.now(timezone.utc).isoformat()
            cfg = self._configs.get("front", SessionConfig(role="front"))
            # Named hold locks measurement; free recording keeps current (often auto).
            new_stance = stance_key or cfg.stance or AUTO_STANCE
            self._configs["front"] = SessionConfig(
                source=src, stance=new_stance, view_mode=cfg.view_mode, role="front",
            )
            # Keep an existing live session's capture; only refresh its config
            # so the measured stance matches the exercise being recorded.
            session = self._sessions.get("front")
            if session is not None:
                session.config = self._configs["front"]
            else:
                self._sessions["front"] = LiveSession(self._configs["front"], manager=self)
        self._write_recording_marker(safe, seconds)
        return {
            "ok": True, "exercise": safe, "seconds": seconds, "mode": "live",
            "pid": os.getpid(), "started": self._tee_started,
        }

    def tee_frame(self, frame, landmarks, elapsed_s: float) -> None:
        with self._lock:
            tee = self._tee
        if tee is None or tee.finished:
            return
        status = tee.push(frame, landmarks, elapsed_s)
        if status == "time_up":
            self._finish_recording(seal=True)

    def stop_recording(self, seal: bool = False) -> dict[str, Any]:
        return self._finish_recording(seal=seal)

    def _finish_recording(self, seal: bool) -> dict[str, Any]:
        with self._lock:
            tee = self._tee
            self._tee = None
            self._tee_started = None
        self._clear_recording_marker()
        if tee is None:
            return {"stopped": 0, "note": "No recording was running."}
        recording = tee.finalize(seal=seal)
        if recording is None:
            return {
                "stopped": 1,
                "sealed": False,
                "note": "Recording stopped — no frames were captured.",
            }
        if seal:
            return {
                "stopped": 1,
                "sealed": True,
                "exercise": recording.exercise,
                "video_path": recording.video_path,
                "note": "Recording sealed into the Dojo Record.",
            }
        return {
            "stopped": 1,
            "sealed": False,
            "exercise": recording.exercise,
            "video_path": recording.video_path,
            "note": "Recording stopped - video kept, manifest not sealed.",
        }

    def _write_recording_marker(self, exercise: str, seconds: int) -> None:
        from chirox.config import DATA_DIR

        marker = DATA_DIR / "recording_status.json"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({
            "exercise": exercise,
            "pid": os.getpid(),
            "seconds": seconds,
            "started": self._tee_started,
            "mode": "live",
        }), encoding="utf-8")

    @staticmethod
    def _clear_recording_marker() -> None:
        from chirox.config import DATA_DIR

        marker = DATA_DIR / "recording_status.json"
        try:
            marker.unlink()
        except OSError:
            pass

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
                self._sessions[role] = LiveSession(config, manager=self)
            return self._sessions[role]

    def clear(self, session: LiveSession) -> None:
        with self._lock:
            for role, current in list(self._sessions.items()):
                if current is session:
                    self._sessions.pop(role, None)
