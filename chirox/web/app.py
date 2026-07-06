"""Local browser cockpit for Chirox."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from chirox.calendar import dojo_day
from chirox.config import CODEX_PATH, Config
from chirox.record.codex import Codex
from chirox.vision.tracker import default_model_path
from chirox.web.live import LiveSessionManager, SessionConfig, camera_health, known_cameras

STATIC_DIR = Path(__file__).resolve().parent / "static"
REFERENCE_DIR = Path(__file__).resolve().parents[1] / "reference"
manager = LiveSessionManager()
app = FastAPI(title="Chirox Live Mirror")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
if REFERENCE_DIR.exists():
    app.mount("/reference", StaticFiles(directory=REFERENCE_DIR), name="reference")


@app.middleware("http")
async def no_stale_cockpit(request, call_next):
    """The browser must never show yesterday's cockpit: the launcher always
    serves what is on disk, so the client must always re-fetch it."""
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


class StartRequest(BaseModel):
    source: int | str = 0
    stance: str = "horse"
    view_mode: str = "overlay"
    role: str = "front"


class DualStartRequest(BaseModel):
    front_source: int | str = 0
    side_source: int | str = 2
    stance: str = "horse"
    view_mode: str = "overlay"


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def status():
    config = Config.load()
    day = dojo_day(config.practice_start_date)
    codex = Codex(CODEX_PATH)
    ok, err = codex.verify()
    model_path = default_model_path()
    return {
        "practice": {
            "start": config.practice_start,
            "day_number": day.day_number,
            "week_number": day.week_number,
            "phase": day.phase,
            "phase_focus": day.phase_focus,
        },
        "model": config.model,
        "camera_defaults": {cam["role"]: cam["source"] for cam in known_cameras()},
        "pose_model": {"path": str(model_path), "present": model_path.exists()},
        "codex": {"ok": ok, "error": err},
        "session": {
            "active": manager.active(),
            "active_roles": manager.active_roles(),
            "config": asdict(manager.config),
            "configs": manager.configs(),
        },
    }


@app.get("/api/cameras")
def cameras():
    # Cameras are exclusive-access on Windows: probing a source a live session
    # holds would report a working camera as broken (or fight it for the device).
    active = manager.active_sources()
    items = []
    for cam in known_cameras():
        if str(cam["source"]) in active:
            items.append({**cam, "opened": True, "read": None, "width": None, "height": None, "in_use": True})
        else:
            items.append({**cam, **camera_health(cam["source"]), "in_use": False})
    return {"cameras": items}


@app.post("/api/session/start")
def start_session(req: StartRequest):
    config = SessionConfig(source=req.source, stance=req.stance, view_mode=req.view_mode, role=req.role)
    return manager.start(config)


@app.post("/api/session/start-dual")
def start_dual_session(req: DualStartRequest):
    return manager.start_dual(
        SessionConfig(source=req.front_source, stance=req.stance, view_mode=req.view_mode, role="front"),
        SessionConfig(source=req.side_source, stance=req.stance, view_mode=req.view_mode, role="side"),
    )


class RoleRequest(BaseModel):
    role: str


@app.post("/api/session/stop-role")
def stop_role_session(req: RoleRequest):
    """Stop one live view (used to swap the third camera in — measured hub
    truth 2026-07-03: three simultaneous streams collapse to 0fps, two hold)."""
    return manager.stop_role(req.role)


@app.post("/api/session/stop")
def stop_session():
    return manager.stop_all()


# --- control deck: every organ, launchable by button (no terminal required) -----


class ReadRequest(BaseModel):
    label: str


class TrainRequest(BaseModel):
    stances: list[str] | None = None
    seconds: int = 60
    drills: int = 3
    source: int | str = 0


class RecordRequest(BaseModel):
    exercise: str
    source: int | str = 0
    seconds: int = 60
    stance: str | None = None


class MasterRequest(BaseModel):
    question: str | None = None
    reflect: bool = False


class ForgetRequest(BaseModel):
    seq: int
    reason: str


class SpeakRequest(BaseModel):
    text: str


class ModeRequest(BaseModel):
    mode: str


class LearningRecordRequest(BaseModel):
    day_number: int
    date: str | None = None
    data: dict = Field(default_factory=dict)


@app.get("/api/control/status")
def control_status():
    from chirox.web import control

    from chirox.activity import read_activity

    return {"ear": control.ear_status(), "voice": control.voice_activity(),
            "codex": control.verify_codex(), "activity": read_activity()}


@app.get("/api/mode")
def get_mode():
    from chirox.activity import read_activity

    return read_activity()


@app.post("/api/mode")
def post_mode(req: ModeRequest):
    from chirox.web.learning import switch_mode

    if req.mode == "learning":
        manager.stop_all()
    return switch_mode(req.mode)


@app.post("/api/control/ear/start")
def control_ear_start():
    from chirox.web import control

    return control.start_ear()


@app.post("/api/control/ear/stop")
def control_ear_stop():
    from chirox.web import control

    return control.stop_ear()


@app.post("/api/control/silence")
def control_silence():
    from chirox.web import control

    return control.silence()


@app.get("/api/library")
def library():
    from chirox.web import control

    return {"items": control.library_items()}


@app.post("/api/library/read")
def library_read(req: ReadRequest):
    from chirox.web import control

    return control.start_reading(req.label)


@app.get("/api/learning")
def learning_overview():
    from chirox.web import learning

    return learning.overview()


@app.get("/api/learning/day/{day_number}")
def learning_day(day_number: int):
    from chirox.web import learning

    return learning.record_day(day_number)


@app.post("/api/learning/daily")
def learning_save_daily(req: LearningRecordRequest):
    from chirox.web import learning

    return learning.save_daily(req.day_number, req.date, req.data)


@app.post("/api/learning/mandarin")
def learning_save_mandarin(req: LearningRecordRequest):
    from chirox.web import learning

    return learning.save_mandarin(req.day_number, req.date, req.data)


@app.get("/api/train/catalog")
def train_catalog():
    from chirox.web.guides import drill_guides

    return {"drills": drill_guides()["drills"]}


@app.get("/api/guides")
def guides():
    from chirox.web.guides import drill_guides

    return drill_guides()


@app.post("/api/train/start")
def train_start(req: TrainRequest):
    from chirox.web import control

    manager.stop_all()  # the trainer needs the camera; the mirror yields
    return control.start_training(req.stances, req.seconds, req.drills, str(req.source))


@app.post("/api/record/start")
def record_start(req: RecordRequest):
    from chirox.web import control

    manager.stop_all()  # the recorder needs the camera; the mirror yields
    return control.start_recording(req.exercise, str(req.source), req.seconds, req.stance)


@app.post("/api/record/stop")
def record_stop():
    from chirox.web import control

    return control.stop_recording()


@app.get("/api/timeline")
def get_timeline(limit: int = 20):
    from chirox.web import control

    return {"events": control.timeline(limit)}


@app.post("/api/master/debrief")
def master_debrief(req: MasterRequest):
    from chirox.web import control

    return control.ask_master(req.question, reflect=req.reflect)


@app.get("/api/memory")
def memory_list(last: int = 20):
    from chirox.web import control

    return control.list_memory(last)


@app.post("/api/memory/forget")
def memory_forget(req: ForgetRequest):
    from chirox.web import control

    return control.forget_memory(req.seq, req.reason)


@app.post("/api/say")
def say(req: SpeakRequest):
    from chirox.web import control

    return control.speak_text(req.text)


@app.websocket("/ws/live")
async def live_socket(websocket: WebSocket):
    await live_role_socket(websocket, "front")


@app.websocket("/ws/live/{role}")
async def live_role_socket(websocket: WebSocket, role: str):
    await websocket.accept()
    session = manager.current(role)
    try:
        async for message in session.frames():
            if isinstance(message, bytes):
                await websocket.send_bytes(message)  # packed frame (header + JPEG)
            else:
                await websocket.send_json(message)   # error payloads stay JSON
    except WebSocketDisconnect:
        session.stop()
    finally:
        session.close()
        manager.clear(session)


def main() -> None:
    import uvicorn

    uvicorn.run("chirox.web.app:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    main()
