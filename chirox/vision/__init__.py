"""The Reflex — deterministic measurement of the body.

Pure geometry, hardcoded physics. **No generative model touches form
assessment.** The machine measures and reports, with explicit uncertainty when
the landmarks are not clearly seen. It never claims a stance is correct on faith.

    stances.py   — pure, unit-testable geometry (no camera, no mediapipe)
    schema.py    — the session payload contract
    multicam.py  — fuse front + side cameras (the Weatherman rig)
    pipeline.py  — the live/video runner (imports mediapipe + opencv)
"""
