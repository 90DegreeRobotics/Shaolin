# Privacy
## What Stays Local

The practitioner's body, voice, record, and training media stay local by
default.

Chirox stores runtime data under git-ignored Dojo paths:

- `Dojo/data/`
- `Dojo/media/`
- `Dojo/models/`
- `Dojo/voice/`

The public repository should contain manuals, source code, templates, tests,
sample fixtures, and witness artifacts that have been reviewed for personal
data. It should not contain private logs, private video, private audio, or local
operator secrets.

## What May Be Sealed Locally

The append-only Dojo Record may seal:

- daily, weekly, monthly, and Mandarin entries
- training-call summaries
- deterministic vision measurements
- session-recording manifests
- conversation records
- growth-dialogue records

Those records are local practice data. They are evidence for the practitioner,
not public content.

## Public Witness Artifacts

A public witness artifact should include only what proves the claim:

- command run
- date
- environment notes
- redacted or synthetic output
- limitation observed

If an artifact includes camera, voice, room, location, health, or personal
routine information, keep it local or redact it before committing.

## No Hidden Uploads

No Chirox path should upload practice data to a third-party service as a hidden
side effect. If future work adds optional sync, remote access, or sharing, it
must be explicit, documented, and off by default.

