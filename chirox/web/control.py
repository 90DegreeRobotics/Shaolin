"""The cockpit's control plane — every Chirox organ, launchable by button.

This is a training system, not a terminal: the practitioner runs ONE launcher
and controls everything else from the browser. Each function here wraps an
organ the CLI already proved out — the web layer adds no new behavior, only
reach. Subprocesses are used for anything that speaks or holds a camera for
long (narration, training, recording) so the server stays responsive and the
ear's "Chirox, stop" / Ctrl+Alt+0 kill switch keeps working unchanged.

Local-only, same as the rest of the cockpit: 127.0.0.1.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


# --- process plumbing -------------------------------------------------------------


def list_python_processes() -> list[tuple[int, str]]:
    """(pid, command line) for every python process. Windows: via PowerShell."""
    if sys.platform != "win32":
        return []
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=15,
        ).stdout.strip()
        if not out:
            return []
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        return [(int(p["ProcessId"]), p.get("CommandLine") or "") for p in data]
    except Exception:
        return []


def find_pids(marker: str) -> list[int]:
    return [pid for pid, cmd in list_python_processes() if marker in cmd]


def terminate(pid: int) -> None:
    if sys.platform == "win32":
        import ctypes

        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
        if h:
            k.TerminateProcess(h, 0)
            k.CloseHandle(h)
    else:
        import os
        import signal

        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass


def _spawn(module_args: list[str]) -> int:
    from chirox.config import REPO_ROOT

    proc = subprocess.Popen([sys.executable, "-m", *module_args], cwd=str(REPO_ROOT),
                            creationflags=_NO_WINDOW,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc.pid


# --- the ear ------------------------------------------------------------------------


def ear_status() -> dict:
    pids = find_pids("chirox.listener")
    return {"running": bool(pids), "pid": pids[0] if pids else None}


def start_ear() -> dict:
    if ear_status()["running"]:
        return {**ear_status(), "note": "already running"}
    pid = _spawn(["chirox.listener"])
    return {"running": True, "pid": pid}


# --- waking the Master (Ollama + the ear, one button) ----------------------------


def ollama_status() -> dict:
    import requests

    from chirox.config import Config

    config = Config.load()
    try:
        r = requests.get(f"{config.ollama_url.rstrip('/')}/api/tags", timeout=2)
        r.raise_for_status()
        return {"running": True}
    except Exception:
        return {"running": False}


def wake_master() -> dict:
    """The practitioner presses ONE button: Ollama comes up if it is down,
    then the ear starts listening. Honest result either way."""
    import time

    started_ollama = False
    if not ollama_status()["running"]:
        try:
            subprocess.Popen(["ollama", "serve"], creationflags=_NO_WINDOW,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            started_ollama = True
        except FileNotFoundError:
            return {"ok": False, "ollama": {"running": False, "started": False},
                    "ear": ear_status(),
                    "error": "Ollama is not installed or not on PATH on this machine."}
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if ollama_status()["running"]:
                break
            time.sleep(0.5)
    ollama = {**ollama_status(), "started": started_ollama}
    ear = start_ear()
    ok = ollama["running"] and bool(ear.get("running"))
    out = {"ok": ok, "ollama": ollama, "ear": ear}
    if not ollama["running"]:
        out["error"] = "Ollama did not come up within 15 seconds — check the installation."
    return out


def stop_ear() -> dict:
    pids = find_pids("chirox.listener")
    for pid in pids:
        terminate(pid)
    return {"running": False, "stopped": len(pids)}


# --- voice activity (narration / training / recording) --------------------------------


def voice_activity() -> dict:
    """What is Chirox doing out loud right now?"""
    from chirox.narrator import narration_pid

    pid = narration_pid()
    kind = None
    if pid is not None:
        cmds = {p: c for p, c in list_python_processes()}
        cmd = cmds.get(pid, "")
        kind = "training" if "chirox.trainer" in cmd else "reading"
    rec_info = recording_status()
    rec = rec_info["recording"] or bool(find_pids("chirox.cli record") or find_pids('"record"'))
    return {"active": pid is not None, "pid": pid, "kind": kind,
            "recording": rec, "recording_info": rec_info}


def silence() -> dict:
    """The cockpit's red button: kill narration/training and stop local speakers.

    Does not stop the ear process itself — toggle WAKE off (or say
    "Chirox, go to sleep") for that. Stops whatever is holding the shared
    narration PID lock and asks PortAudio to abort any in-process playback
    in this server (short ``speak_text`` replies).
    """
    from chirox.narrator import stop_narration

    stopped = stop_narration()
    # Also kill stray trainer/narrator processes if the lock was already cleared.
    extra = 0
    for pid, cmd in list_python_processes():
        if "chirox.narrator" in cmd or "chirox.trainer" in cmd:
            terminate(pid)
            extra += 1
    try:
        import sounddevice as sd

        sd.stop()
    except Exception:
        pass
    return {"stopped": bool(stopped or extra), "narration": stopped, "extra_killed": extra}


# --- library ---------------------------------------------------------------------------


def library_items() -> list[dict]:
    from chirox.narrator import readable_catalog, reading_progress

    progress = reading_progress()
    items = []
    for label, _keys, path in readable_catalog():
        items.append({
            "label": label,
            "file": path.name,
            "kind": "book" if path.suffix == ".txt" else "doc",
            "bookmark": progress.get(path.name, 0),
        })
    return items


def start_reading(label: str) -> dict:
    from chirox.narrator import readable_catalog, spawn_narration, stop_narration

    for item_label, _keys, path in readable_catalog():
        if item_label == label:
            stop_narration()  # one voice at a time
            pid = spawn_narration(path)
            return {"ok": True, "label": item_label, "pid": pid}
    return {"ok": False, "error": f"unknown title: {label}"}


# --- training ----------------------------------------------------------------------------


def start_training(stances: list[str] | None, seconds: int, drills: int, source: str = "0") -> dict:
    from chirox.narrator import stop_narration
    from chirox.vision.reps import REP_CATALOG
    from chirox.vision.stances import STANCES

    if stances:
        for s in stances:
            if s not in STANCES and s not in REP_CATALOG:
                return {"ok": False, "error": f"unknown stance: {s}"}
    stop_narration()
    args = ["chirox.trainer", "--source", str(source), "--seconds", str(seconds), "--drills", str(drills)]
    if stances:
        args += ["--stances", ",".join(stances)]
    pid = _spawn(args)
    return {"ok": True, "pid": pid}


# --- recording -----------------------------------------------------------------------------

# The recording marker: the single honest answer to "am I being recorded?".
# Written on start, cleared on stop; a dead pid invalidates it automatically.


def _recording_marker():
    from chirox.config import DATA_DIR

    return DATA_DIR / "recording_status.json"


def recording_status() -> dict:
    """Is a recording running RIGHT NOW — and of what, since when?"""
    from chirox.web.live import cockpit_manager

    mgr = cockpit_manager()
    if mgr is not None and mgr.is_recording():
        return mgr.recording_info()
    marker = _recording_marker()
    if not marker.exists():
        return {"recording": False}
    try:
        info = json.loads(marker.read_text(encoding="utf-8"))
    except Exception:
        return {"recording": False}
    # Live-tee markers are owned by the cockpit process; CLI markers by a child.
    alive = any(pid == info.get("pid") for pid, _ in list_python_processes())
    if not alive:
        try:
            marker.unlink()
        except OSError:
            pass
        return {"recording": False}
    return {"recording": True, "exercise": info.get("exercise"),
            "started": info.get("started"), "seconds": info.get("seconds"),
            "mode": info.get("mode", "cli")}


def stop_recording() -> dict:
    """Kill a recording early. Honest consequence: the video file survives but
    the manifest is NOT sealed — an aborted session is not evidence."""
    from chirox.web.live import cockpit_manager

    mgr = cockpit_manager()
    if mgr is not None and mgr.is_recording():
        return mgr.stop_recording(seal=False)
    pids = [pid for pid, cmd in list_python_processes()
            if "chirox.cli" in cmd and "record" in cmd]
    for pid in pids:
        terminate(pid)
    try:
        _recording_marker().unlink()
    except OSError:
        pass
    return {"stopped": len(pids),
            "note": "Recording stopped - video kept, manifest not sealed." if pids else "No recording was running."}


def start_recording(exercise: str, source: str, seconds: int, stance: str | None,
                    live: bool = True) -> dict:
    """Start a recording. Cockpit default is live-tee (Wireguy keeps the camera).

    ``live=False`` keeps the headless CLI recorder for terminal use / tests.
    """
    from datetime import datetime, timezone

    from chirox.web.live import cockpit_manager

    if not exercise.strip():
        return {"ok": False, "error": "exercise name is required"}
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in exercise.strip().lower())
    mgr = cockpit_manager()
    if live and mgr is not None:
        return mgr.begin_recording(safe, source, seconds, stance)
    args = ["chirox.cli", "record", "--exercise", safe, "--source", str(source),
            "--seconds", str(seconds), "--no-show"]
    if stance:
        args += ["--stance", stance]
    pid = _spawn(args)
    marker = _recording_marker()
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({
        "exercise": safe, "pid": pid, "seconds": seconds,
        "started": datetime.now(timezone.utc).isoformat(),
        "mode": "cli",
    }), encoding="utf-8")
    return {"ok": True, "exercise": safe, "pid": pid, "seconds": seconds, "mode": "cli"}


def _recording_target(file: str) -> Path | None:
    from chirox.config import MEDIA_DIR

    if not file or Path(file).is_absolute():
        return None
    root = MEDIA_DIR.resolve()
    target = (root / file).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    if not target.exists() or not target.is_file():
        return None
    return target


def _media_url(path: Path) -> str:
    from chirox.config import MEDIA_DIR

    rel = path.resolve().relative_to(MEDIA_DIR.resolve())
    return "/media/" + quote(str(rel).replace("\\", "/"), safe="/")


def _mjpeg_url(file: str) -> str:
    return "/api/recordings/mjpeg?file=" + quote(file, safe="")


def _playback_proxy_path(target: Path) -> Path:
    from chirox.config import MEDIA_DIR

    digest = hashlib.sha1(str(target.resolve()).encode("utf-8")).hexdigest()[:12]
    safe_stem = "".join(c if c.isalnum() or c in "_-" else "_" for c in target.stem)[:80]
    return MEDIA_DIR / "_playback" / f"{safe_stem}.{digest}.browser.mp4"


def _cached_playback_proxy(target: Path) -> Path | None:
    proxy = _playback_proxy_path(target)
    try:
        if proxy.exists() and proxy.stat().st_size > 0 and proxy.stat().st_mtime >= target.stat().st_mtime:
            return proxy
    except OSError:
        return None
    return None


def playback_recording(file: str) -> dict:
    """Return the fastest browser URL for a recording without doing heavy work."""
    target = _recording_target(file)
    if target is None:
        return {"ok": False, "error": "no such recording"}
    proxy = _cached_playback_proxy(target)
    return {
        "ok": True,
        "file": file,
        "url": _media_url(proxy or target),
        "original_url": _media_url(target),
        "proxy_ready": proxy is not None,
        "can_prepare": shutil.which("ffmpeg") is not None,
    }


def prepare_playback(file: str) -> dict:
    """Make a browser-playable H.264 proxy without changing the evidence file."""
    target = _recording_target(file)
    if target is None:
        return {"ok": False, "error": "no such recording"}
    cached = _cached_playback_proxy(target)
    if cached is not None:
        return {"ok": True, "url": _media_url(cached), "proxy_ready": True, "cached": True}

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return {
            "ok": False,
            "url": _media_url(target),
            "mjpeg_url": _mjpeg_url(file),
            "proxy_ready": False,
            "error": "Using streaming replay because ffmpeg is not available.",
        }

    proxy = _playback_proxy_path(target)
    proxy.parent.mkdir(parents=True, exist_ok=True)
    tmp = proxy.with_suffix(".tmp.mp4")
    try:
        if tmp.exists():
            tmp.unlink()
    except OSError:
        pass

    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(target),
        "-map", "0:v:0",
        "-an",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(tmp),
    ]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=240, creationflags=_NO_WINDOW)
    except Exception as exc:
        return {
            "ok": False, "url": _media_url(target), "mjpeg_url": _mjpeg_url(file),
            "proxy_ready": False, "error": str(exc),
        }
    if done.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        try:
            tmp.unlink()
        except OSError:
            pass
        error = (done.stderr or done.stdout or "ffmpeg could not prepare this recording").strip()
        return {
            "ok": False, "url": _media_url(target), "mjpeg_url": _mjpeg_url(file),
            "proxy_ready": False, "error": error[-300:],
        }
    tmp.replace(proxy)
    return {"ok": True, "url": _media_url(proxy), "proxy_ready": True, "cached": False}


def mjpeg_recording(file: str):
    """Stream a recording as MJPEG for browsers that reject the MP4 codec."""
    target = _recording_target(file)
    if target is None:
        return None

    def frames():
        import time

        import cv2

        cap = cv2.VideoCapture(str(target))
        fps = cap.get(cv2.CAP_PROP_FPS) or 20
        delay = min(0.1, max(0.025, 1 / fps))
        try:
            while cap.isOpened():
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                encoded, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                if encoded:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Cache-Control: no-cache\r\n\r\n" +
                        buf.tobytes() +
                        b"\r\n"
                    )
                time.sleep(delay)
        finally:
            cap.release()

    return frames()


def list_recordings(limit: int = 30) -> dict:
    """Every training video in the archive, newest first — sealed manifests
    joined to the files so the practitioner sees date, day, duration, size,
    and exactly where the file lives."""
    from chirox.config import CODEX_PATH, MEDIA_DIR
    from chirox.record.codex import Codex

    manifests: dict[str, dict] = {}
    for e in Codex(CODEX_PATH).events("session_recording"):
        p = e.payload
        try:
            key = str(Path(p.get("video_path", "")).resolve())
        except OSError:
            continue
        manifests[key] = p

    items = []
    if MEDIA_DIR.exists():
        for f in MEDIA_DIR.rglob("*.mp4"):
            rel = f.relative_to(MEDIA_DIR)
            if rel.parts and rel.parts[0] == "_playback":
                continue
            m = manifests.get(str(f.resolve()))
            stat = f.stat()
            proxy = _cached_playback_proxy(f)
            items.append({
                "file": str(rel).replace("\\", "/"),
                "url": _media_url(f),
                "play_url": _media_url(proxy or f),
                "proxy_ready": proxy is not None,
                "exercise": m.get("exercise") if m else rel.parts[0] if len(rel.parts) > 1 else "unknown",
                "date": m.get("date") if m else None,
                "day_number": m.get("day_number") if m else None,
                "duration_s": m.get("duration_s") if m else None,
                "size_mb": round(stat.st_size / (1024 * 1024), 1),
                "modified": stat.st_mtime,
                "sealed": m is not None,
            })
    items.sort(key=lambda r: r["modified"], reverse=True)
    return {"ok": True, "folder": str(MEDIA_DIR), "items": items[:limit]}


def open_recording(file: str) -> dict:
    """Open one recording in the system player — playback that always works,
    whatever codec the writer used."""
    import os

    target = _recording_target(file)
    if target is None:
        return {"ok": False, "error": "no such recording"}
    if sys.platform == "win32":
        os.startfile(str(target))  # noqa: S606 — local operator opening his own file
        return {"ok": True}
    return {"ok": False, "error": "opening files is only wired for Windows"}


def open_media_folder() -> dict:
    import os

    from chirox.config import MEDIA_DIR

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        os.startfile(str(MEDIA_DIR))  # noqa: S606
        return {"ok": True, "folder": str(MEDIA_DIR)}
    return {"ok": False, "folder": str(MEDIA_DIR), "error": "only wired for Windows"}


# --- record & master --------------------------------------------------------------------


def timeline(limit: int = 20) -> list[dict]:
    from chirox.config import CODEX_PATH
    from chirox.record.codex import Codex

    codex = Codex(CODEX_PATH)
    rows: list[dict] = []
    for e in codex.events():
        if e.type == "session_recording":
            p = e.payload
            rows.append({"type": "recording", "date": p.get("date"), "day": p.get("day_number"),
                         "what": p.get("exercise"), "detail": f"{p.get('duration_s')}s, conf {p.get('mean_confidence')}"})
        elif e.type == "training_call":
            drills = e.payload.get("drills", [])
            summary = ", ".join(f"{d.get('stance')} {int(d.get('form_rate', 0) * 100)}%" for d in drills)
            rows.append({"type": "training", "date": e.payload.get("started", "")[:10], "day": None,
                         "what": f"{len(drills)} drills", "detail": summary or "no drills measured"})
        elif e.type == "vision_session":
            p = e.payload
            rows.append({"type": "stance", "date": p.get("started", "")[:10], "day": None,
                         "what": p.get("stance"), "detail": p.get("assessment", "")[:80]})
        elif e.type == "routine_session":
            p = e.payload
            totals = p.get("totals") or {}
            rows.append({
                "type": "routine",
                "date": p.get("date") or (p.get("started") or "")[:10],
                "day": p.get("day_number"),
                "what": p.get("label") or p.get("routine_key"),
                "detail": (
                    f"{totals.get('phases_completed', 0)}/{totals.get('phases_total', '?')} phases, "
                    f"{totals.get('reps_total', 0)} reps, {totals.get('duration_s', 0)}s"
                ),
            })
        elif e.type == "match_session":
            p = e.payload
            mean = p.get("mean_score")
            band = p.get("in_band_ratio")
            rows.append({
                "type": "verify",
                "date": p.get("date") or (p.get("started") or "")[:10],
                "day": p.get("day_number"),
                "what": p.get("label") or p.get("target_key") or "verify",
                "detail": (
                    f"mean {mean if mean is not None else '—'}, "
                    f"in-band {int((band or 0) * 100)}%, "
                    f"best {p.get('best_score') if p.get('best_score') is not None else '—'}"
                ),
            })
    return rows[-limit:][::-1]


def ask_master(question: str | None, reflect: bool = False) -> dict:
    from chirox.config import Config
    from chirox.master.brain import MasterUnavailable, Ollama, converse, debrief, seal_exchange

    config = Config.load()
    ok, reason = Ollama(config).available()
    if not ok:
        return {"ok": False, "text": f"The Master is silent — he will not fabricate. {reason}"}
    try:
        if reflect:
            q = (question or "").strip() or "Look back over my path with me."
            text = converse(config, question=q, reflect=True)
            seal_exchange(q, text, config)
            return {"ok": True, "text": text}
        if question and question.strip():
            q = question.strip()
            text = converse(config, question=q)
            seal_exchange(q, text, config)
            return {"ok": True, "text": text}
        return {"ok": True, "text": debrief(config, question=None)}
    except MasterUnavailable as exc:
        return {"ok": False, "text": f"The Master is silent — he will not fabricate. {exc}"}


# --- the Master's memory (list + recorded forgetting) ---------------------------------


def list_memory(last: int = 20) -> dict:
    """Sealed conversations the Master can recall — newest first."""
    from chirox.config import CODEX_PATH
    from chirox.record.codex import Codex

    codex = Codex(CODEX_PATH)
    forgotten = {e.payload.get("target_seq") for e in codex.events("forget")}
    rows = []
    for e in list(codex.events("conversation"))[-last:]:
        rows.append({
            "seq": e.seq,
            "at": str(e.payload.get("at") or e.ts)[:16].replace("T", " "),
            "question": " ".join(str(e.payload.get("question", "")).split()),
            "answer": " ".join(str(e.payload.get("answer", "")).split()),
            "forgotten": e.seq in forgotten,
        })
    return {"ok": True, "items": rows[::-1]}


def forget_memory(seq: int, reason: str) -> dict:
    """Withdraw one sealed exchange from recall — recorded, never silent."""
    from chirox.config import CODEX_PATH, Config
    from chirox.record.codex import Codex
    from chirox.sentinel import Sentinel

    if not (reason or "").strip():
        return {"ok": False, "error": "a reason is required — erasure is recorded, never silent"}
    config = Config.load()
    codex = Codex(CODEX_PATH)
    target = next((e for e in codex.events("conversation") if e.seq == int(seq)), None)
    if target is None:
        return {"ok": False, "error": f"no conversation at seq {seq}"}
    sentinel = Sentinel(codex, config)
    sentinel.init_operator()
    grant = sentinel.authorize("record.forget")
    event = codex.forget(int(seq), reason.strip(), operator=config.operator_id)
    sentinel.consume(grant)
    return {"ok": True, "sealed_at": event.seq}


def speak_text(text: str) -> dict:
    if not text.strip():
        return {"ok": False, "error": "nothing to speak"}
    pid = _spawn(["chirox.cli", "say", text[:1200]])
    return {"ok": True, "pid": pid}


def verify_codex() -> dict:
    from chirox.config import CODEX_PATH
    from chirox.record.codex import Codex

    codex = Codex(CODEX_PATH)
    ok, err = codex.verify()
    n = len(list(codex.events()))
    return {"ok": ok, "events": n, "error": err}
