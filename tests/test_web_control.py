"""Control-deck endpoints — everything launchable by button, no terminal.

Process-spawning paths are monkeypatched: these tests prove routing, validation,
and honest error shapes, not that Windows can start python (the smoke run does)."""

from fastapi.testclient import TestClient

from chirox.web import control
from chirox.web.app import app

client = TestClient(app)


def test_control_status_shape(monkeypatch):
    monkeypatch.setattr(control, "list_python_processes", lambda: [(111, "python -m chirox.listener")])
    data = client.get("/api/control/status").json()
    assert data["ear"]["running"] is True
    assert data["ear"]["pid"] == 111
    assert "voice" in data
    assert "codex" in data


def test_ear_stop_reports_count(monkeypatch):
    killed = []
    monkeypatch.setattr(control, "list_python_processes", lambda: [(7, "python -m chirox.listener")])
    monkeypatch.setattr(control, "terminate", lambda pid: killed.append(pid))
    data = client.post("/api/control/ear/stop").json()
    assert data == {"running": False, "stopped": 1}
    assert killed == [7]


def test_library_lists_books_and_docs():
    data = client.get("/api/library").json()
    labels = {i["label"] for i in data["items"]}
    assert "the manual" in labels
    assert "the Kung Fu study guide" in labels
    assert "Tao Te Ching" in labels
    kinds = {i["kind"] for i in data["items"]}
    assert kinds <= {"book", "doc"}


def test_library_read_unknown_title_is_honest():
    data = client.post("/api/library/read", json={"label": "War and Peace"}).json()
    assert data["ok"] is False
    assert "unknown title" in data["error"]


def test_train_start_rejects_unknown_stance():
    data = client.post("/api/train/start", json={"stances": ["backflip"]}).json()
    assert data["ok"] is False
    assert "unknown stance" in data["error"]


def test_train_start_spawns_with_chosen_drills(monkeypatch):
    spawned = []
    monkeypatch.setattr(control, "_spawn", lambda args: spawned.append(args) or 4242)
    data = client.post("/api/train/start",
                       json={"stances": ["horse", "crane"], "seconds": 45, "drills": 2}).json()
    assert data == {"ok": True, "pid": 4242}
    args = spawned[0]
    assert args[0] == "chirox.trainer"
    assert "horse,crane" in args
    assert "45" in args


def test_record_start_requires_exercise_name():
    data = client.post("/api/record/start", json={"exercise": "   "}).json()
    assert data["ok"] is False


def test_record_start_sanitizes_exercise(monkeypatch):
    spawned = []
    monkeypatch.setattr(control, "_spawn", lambda args: spawned.append(args) or 9)
    data = client.post("/api/record/start",
                       json={"exercise": "Eight Brocades!", "seconds": 60}).json()
    assert data["ok"] is True
    assert data["exercise"] == "eight_brocades_"
    assert "--no-show" in spawned[0]


def test_say_refuses_empty_text():
    data = client.post("/api/say", json={"text": "  "}).json()
    assert data["ok"] is False


def test_frontend_has_command_deck():
    text = client.get("/").text
    for element in ("silenceButton", "trainGo", "libraryList",
                    "recordGo", "masterAskBtn", "timelineList",
                    "practiceStage", "pickWorkBtn"):
        assert element in text, element
    assert "swapBtn" not in text


def test_record_stop_honest_when_nothing_running(monkeypatch):
    monkeypatch.setattr(control, "list_python_processes", lambda: [])
    data = client.post("/api/record/stop").json()
    assert data["stopped"] == 0
    assert "No recording" in data["note"]


def test_stop_role_endpoint():
    data = client.post("/api/session/stop-role", json={"role": "side"}).json()
    assert data == {"active": False, "role": "side"}
