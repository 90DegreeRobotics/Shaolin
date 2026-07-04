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

import json
import subprocess
import sys
from pathlib import Path

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
    rec = find_pids("chirox.cli record") or find_pids('"record"')
    return {"active": pid is not None, "pid": pid, "kind": kind,
            "recording": bool(rec)}


def silence() -> dict:
    """The cockpit's red button: kill any narration or training session."""
    from chirox.narrator import stop_narration

    return {"stopped": stop_narration()}


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


def stop_recording() -> dict:
    """Kill a recording early. Honest consequence: the video file survives but
    the manifest is NOT sealed — an aborted session is not evidence."""
    pids = [pid for pid, cmd in list_python_processes()
            if "chirox.cli" in cmd and "record" in cmd]
    for pid in pids:
        terminate(pid)
    return {"stopped": len(pids),
            "note": "Recording aborted - video kept, manifest not sealed." if pids else "No recording was running."}


def start_recording(exercise: str, source: str, seconds: int, stance: str | None) -> dict:
    if not exercise.strip():
        return {"ok": False, "error": "exercise name is required"}
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in exercise.strip().lower())
    args = ["chirox.cli", "record", "--exercise", safe, "--source", str(source),
            "--seconds", str(seconds), "--no-show"]
    if stance:
        args += ["--stance", stance]
    pid = _spawn(args)
    return {"ok": True, "exercise": safe, "pid": pid}


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
    return rows[-limit:][::-1]


def ask_master(question: str | None) -> dict:
    from chirox.config import Config
    from chirox.master.brain import MasterUnavailable, Ollama, converse, debrief, seal_exchange

    config = Config.load()
    ok, reason = Ollama(config).available()
    if not ok:
        return {"ok": False, "text": f"The Master is silent — he will not fabricate. {reason}"}
    try:
        if question and question.strip():
            q = question.strip()
            text = converse(config, question=q)
            seal_exchange(q, text, config)
            return {"ok": True, "text": text}
        return {"ok": True, "text": debrief(config, question=None)}
    except MasterUnavailable as exc:
        return {"ok": False, "text": f"The Master is silent — he will not fabricate. {exc}"}


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
