# Chirox Frontend Plan: Live Wireframe Mirror

## Status

COMPLETED (2026-07-01) and then SUPERSEDED (2026-07-04): the cockpit was rebuilt
as a one-page control deck — a toggle row (MIRROR · EAR · TRAIN · READ · RECORD ·
MASTER · SILENCE), three camera boxes with two live at a time (measured hub
limit), chips instead of typing, launched as its own app window from a desktop
shortcut. This document records the original V1 plan.

## Summary

Build a local browser-based Chirox frontend that shows the user's live camera feed with a moving wireframe skeleton overlay. V1 is a testing cockpit, not a recording system: it prioritizes live body tracking, camera setup, deterministic stance feedback, and clear uncertainty states.

Chosen defaults:

- App form: local web app served by Python
- Live view: camera + skeleton overlay
- Recording: out of scope for V1
- Front camera: source `0`
- Side camera: source `2`
- Extra available source: source `1`
- First stance modes: `horse` and `bow`
- Backend source of truth: existing Python Chirox vision stack

## Key Changes

### Backend App Layer

Add a lightweight local web server under Chirox using FastAPI.

Add dependencies:

- `fastapi`
- `uvicorn`
- `websockets`

Expose a local-only server:

- Default host: `127.0.0.1`
- Default port: `8765`
- Launch command: `python -m chirox.web.app`

The backend owns camera capture because the existing OpenCV + MediaPipe + deterministic stance pipeline already works locally.

### API Shape

Provide these minimum endpoints:

- `GET /`: serves the frontend shell.
- `GET /api/status`: returns practice day, configured model, camera defaults, pose model status, and Codex verification status.
- `GET /api/cameras`: returns camera indexes `0`, `2`, and `1`, plus open/read health checks.
- `POST /api/session/start`: starts one live session with `source`, `stance`, and `view_mode`.
- `POST /api/session/stop`: stops the active session and releases the camera.
- `WS /ws/live`: streams live frame and pose data to the browser.

Frame messages include:

- `type`
- `source`
- `timestamp_ms`
- `image_jpeg_base64`
- `landmarks`
- `reading`
- `state`

When no body is detected, `state` is `no_body`, landmarks are empty, and `reading` is `null`.

When landmarks are weak, Chirox's existing uncertainty behavior is preserved and `state` is `uncertain`.

### Vision Integration

Reuse existing Chirox modules:

- `chirox.vision.tracker.PoseTracker`
- `chirox.vision.pipeline.points_from_landmarks`
- `chirox.vision.stances.STANCES`
- `chirox.vision.stances.general_joint_angles`

Do not duplicate stance math in JavaScript. The frontend displays Chirox's deterministic backend verdict.

The live session loop should:

- Open selected camera with OpenCV.
- Read frames continuously.
- Run MediaPipe pose tracking.
- Convert landmarks to named Chirox joints.
- Evaluate selected stance.
- Encode a display frame as JPEG.
- Send frame, landmarks, and reading over WebSocket.
- Release camera cleanly on stop, disconnect, or server shutdown.

### Frontend UI

Create a static frontend served by the Python app:

- `chirox/web/app.py`
- `chirox/web/live.py`
- `chirox/web/static/index.html`
- `chirox/web/static/styles.css`
- `chirox/web/static/app.js`

The first screen is the usable cockpit, not a landing page.

Layout:

- Top bar with title, connection state, camera state, body detection state, and confidence indicator.
- Main live area with canvas camera frame and skeleton overlay.
- Controls for camera, stance, start, stop, mirror, and overlay opacity.
- Metrics panel for assessment, confidence, frames seen, frames uncertain, runtime, angles, and flags.
- Truth panel for `Measured`, `Uncertain`, and `No body detected`.

Visual behavior:

- Skeleton lines use confidence-aware opacity.
- Joint dots fade when visibility is low.
- Stable readings use calm green.
- Warning flags use amber.
- Uncertain states use gray/amber.
- No-body state uses a neutral setup message.
- The interface stays dense, practical, and training-focused.

Skeleton drawing uses the MediaPipe body topology for shoulders, elbows, wrists, hips, knees, and ankles.

## Out Of Scope For V1

Do not build these yet:

- Recording UI
- Sealing sessions into Dojo Record from the frontend
- Timeline browsing
- Master Chirox chat
- Voice controls
- Multi-camera fused verdict
- Packaged desktop app
- Login/auth
- Cloud sync
- Mobile layout beyond basic responsiveness

## Implementation Phases

### Phase 0: Save Plan Doc

Create this document as `plan_2026-07-01_chirox_frontend_live_mirror.md`.

### Phase 1: Backend Server Skeleton

Add `chirox/web/`, static file serving, `/api/status`, `/api/cameras`, and launch via `python -m chirox.web.app`.

Acceptance criteria:

- Browser opens local Chirox page.
- `/api/status` returns JSON.
- `/api/cameras` reports sources `0`, `1`, and `2`.

### Phase 2: Live Camera WebSocket

Implement one active camera session at a time.

Acceptance criteria:

- Starting source `0` streams frames to the browser.
- Stopping releases the camera.
- Switching source stops the previous session before opening the next one.
- Server does not leave camera locked after browser close.

### Phase 3: Skeleton Overlay

Implement frontend canvas rendering.

Acceptance criteria:

- User sees live camera feed.
- Wireframe skeleton moves with the body.
- Low-visibility joints fade.
- No-body state appears clearly when the user leaves frame.

### Phase 4: Deterministic Metrics Panel

Connect backend stance readings to UI.

Acceptance criteria:

- Horse stance displays knee and back angles.
- Bow stance displays front and rear knee angles.
- Flags appear without inventing coaching beyond backend assessment text.
- Low confidence shows `Uncertain`, not a confident verdict.

### Phase 5: Verification

Run:

```powershell
cd C:\shaolin
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m chirox.web.app
```

Manual browser tests:

- Source `0` starts and shows front camera.
- Source `2` starts and shows side camera.
- Skeleton follows body movement.
- Leaving frame shows no-body state.
- Poor framing shows uncertainty.
- Stop button releases camera.
- Refreshing page does not leave stale sessions running.

## Test Plan

Add backend tests:

- Status endpoint returns expected keys.
- Camera endpoint returns structured camera list.
- Stance reading serializer preserves `uncertain`, `confidence`, `metrics`, and `flags`.
- Live session manager replaces an existing session when a new one starts.
- Stop is idempotent.

Add frontend smoke checks:

- Static files are served.
- Main page includes canvas and controls.
- JavaScript handles `frame`, `no_body`, `uncertain`, and error messages.

Manual hardware validation is required because live webcam behavior cannot be fully proven through unit tests.

## Assumptions

- V1 runs only on the local machine.
- Browser UI is acceptable; no desktop packaging yet.
- Backend camera capture remains the source of truth.
- No frontend recording or Dojo sealing in V1.
- Camera `0` is the front view.
- Camera `2` is the side view.
- Camera `1` remains selectable as an extra source.
- Existing Chirox safety rule remains: uncertain evidence must be shown as uncertain.
- Existing local Ollama support is not needed for the first live mirror.
