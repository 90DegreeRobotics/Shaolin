"""One gate to the physical camera — explicit capture settings.

Every module that opens a video source goes through ``open_capture`` so the
rig behaves the same everywhere (live mirror, reflex runner, recorder).

Why explicit settings exist: with no requested size, Windows opens most UVC
webcams — the rig's C920s included — at 640x480, a 4:3 centre crop of the
16:9 sensor. The crop silently narrows the field of view, which reads as
"zoomed in" and pushes stances out of frame. Requesting a 16:9 mode
(1280x720) uses the full sensor width: the widest view the lens can give.
``CAP_PROP_ZOOM`` is also driven to its UVC minimum so a digital zoom left
behind by vendor software cannot keep the frame tight; cameras (or backends)
that do not expose zoom simply ignore the request.

File sources are passed through untouched — capture settings are hardware
properties, and pretending to apply them to a video file would be a lie.
"""

from __future__ import annotations

# The widest honest view: full 16:9 sensor width, no digital zoom.
DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
WIDEST_ZOOM = 100  # UVC zoom_absolute minimum (100 = no zoom on the C920)

# Backend truth for this rig, measured 2026-07-03 (see STATUS.md):
#   - C920s (sources 0 and 2) under Media Foundation: ~2.5s open, 30fps solo,
#     22fps dual through the hub. Under DirectShow they drop to ~10fps.
#   - The "HD 1080P PC-Camera" (source 1) under Media Foundation takes ~40s to
#     open — every time, a driver pathology — but opens in ~2.5s under
#     DirectShow. Its 10fps there is plenty for the extra pose view.
# So each source gets the backend that actually works for it.
DSHOW_SOURCES = {1}


def normalize_source(source) -> int | str:
    """A digit-string is a device index; anything else is a file path."""
    return int(source) if str(source).isdigit() else str(source)


def preferred_backend(source) -> str:
    """'dshow' for devices Media Foundation mishandles; 'default' otherwise. Pure."""
    src = normalize_source(source)
    return "dshow" if isinstance(src, int) and src in DSHOW_SOURCES else "default"


def open_capture(source, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT,
                 zoom: int | None = WIDEST_ZOOM):
    """Open a video source; live cameras get the wide-view settings applied.

    Raises ``RuntimeError`` when the source cannot be opened.
    """
    import sys

    import cv2

    src = normalize_source(source)
    if isinstance(src, int) and sys.platform == "win32":
        backend = cv2.CAP_DSHOW if preferred_backend(src) == "dshow" else cv2.CAP_ANY
        cap = cv2.VideoCapture(src, backend)
        if not cap.isOpened():
            # device indexes can shuffle after replugging — try the other backend
            cap.release()
            other = cv2.CAP_ANY if backend == cv2.CAP_DSHOW else cv2.CAP_DSHOW
            cap = cv2.VideoCapture(src, other)
    else:
        cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(f"could not open video source: {source!r}")
    if isinstance(src, int):
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if zoom is not None:
            cap.set(cv2.CAP_PROP_ZOOM, zoom)
    return cap
