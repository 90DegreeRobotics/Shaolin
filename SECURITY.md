# Security
## Local-First Threat Model

Shaolin and Chirox are designed for local practice. The system should not need
cloud services for the body, voice, Dojo Record, or private practice data.

## Private Data

Treat the following as private by default:

- `Dojo/data/` - local config and append-only Dojo Record
- `Dojo/media/` - recorded training footage
- `Dojo/voice/` - local voice assets and transient audio
- `Dojo/models/` - downloaded model assets
- any live microphone transcript
- any camera frame or video showing the practitioner or their space

Do not commit those paths unless a file is explicitly designed as public sample
data and contains no personal material.

## Reporting A Problem

If you find a security or privacy problem, do not publish private data in an
issue. Report the minimum reproducible facts:

- affected file or command
- what data could leak or be corrupted
- whether it requires local access, network access, or a malicious document
- exact reproduction steps using dummy data

## Chirox Safety Rules

- Local model failure must fail honestly. It must not invent guidance.
- The web deck must remain local-only unless a future change explicitly designs
  and reviews remote access.
- Spoken commands should not perform destructive actions.
- Camera and microphone paths should not write public artifacts by default.
- The red silence path must remain simple and reliable.

## Dependencies

Pinned dependencies live in `requirements.txt`. Before changing versions, run
the full test suite and re-check at least the import path for affected hardware,
voice, or web components.

