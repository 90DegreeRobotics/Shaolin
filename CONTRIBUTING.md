# Contributing
## How To Help Without Weakening The Path

This repository is a public discipline manual and a local-first training tool.
Contributions are welcome when they make the work safer, clearer, more
reproducible, or more honest.

## Ground Rules

- Keep the non-affiliation boundary clear. Do not imply endorsement by Master
  Shi Heng Yi, Shaolin Temple Europe, Shaolin Temple, Songshan Shaolin Temple,
  any Shaolin lineage, any monastery, or any living teacher.
- Do not copy paid course material, private instruction, proprietary manuals,
  or restricted media into this repository.
- Do not add medical, therapeutic, or martial authority claims unless they are
  framed safely and sourced appropriately.
- Do not make Chirox sound more capable than it is. If a feature is not built,
  run, and inspected, call it planned or gated.
- Keep personal practice logs, voice data, camera footage, model files, and
  private Dojo data out of git.
- Prefer small, testable changes over broad rewrites.

## Documentation Standard

Documentation changes should answer at least one of these:

- Does this help a beginner practice safely?
- Does this make the proof path easier to run?
- Does this separate verified software truth from training aspiration?
- Does this prevent injury, false authority, or stale claims?
- Does this make the public gift easier to use without turning it into a
  product funnel?

Avoid glossy self-improvement language. The best pages here either guide
practice, prevent harm, measure progress, or recover from failure.

## Chirox Standard

Chirox is a measuring, recording, retrieval, narration, and reflection system.
It is not a lineage teacher.

Code changes must preserve these rules:

- No generative model may diagnose physical form from vibes.
- Deterministic measurement must keep explicit uncertainty states.
- Flowing forms may be recorded and measured for range of motion, never graded
  as correct by Chirox.
- Personal data belongs in git-ignored runtime paths.
- Consequential writes belong in the append-only Dojo Record through Sentinel.

## Before Submitting Changes

Run:

```powershell
python -m pytest
python -m chirox.cli library
python -m chirox.cli verify
```

For hardware or voice claims, also attach a witness note or update the relevant
proof document. A passing unit test does not prove the live camera, microphone,
speaker, or local model path.

## Licensing

Documentation, curriculum, templates, and planning documents are CC BY-SA 4.0
unless a file says otherwise.

Software code is AGPLv3 unless a file says otherwise. See `LICENSE.md` and
`LICENSE-CODE`.

