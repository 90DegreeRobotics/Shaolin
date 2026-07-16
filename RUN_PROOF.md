# Run Proof
## Stranger Reproducibility Gate

This file is the smallest cold ritual for proving the public parts of Shaolin
from a clean clone. Do not trust claims. Run the commands and inspect the output.

## Baseline Proof

Windows PowerShell:

```powershell
git clone https://github.com/90DegreeRobotics/Shaolin.git
cd Shaolin
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest
python -m chirox.cli init
python -m chirox.cli today
python -m chirox.cli library
python -m chirox.cli log daily --print-template
python -m chirox.cli verify
```

Expected baseline:

- `python -m pytest` passes.
- `init` establishes or confirms the local operator and config.
- `today` prints the current day gate.
- `library` lists readable local docs/books without starting audio or touching
  private practice data.
- `log daily --print-template` prints a blank daily check-in template without
  sealing personal practice data.
- `verify` reports an intact hash-chained Dojo Record.

On macOS/Linux, replace activation with:

```bash
source .venv/bin/activate
```

## Optional Local Model Proof

This path is optional because it requires Ollama and a local model. Chirox must
refuse honestly if the model is unavailable.

```powershell
ollama serve
ollama pull qwen2.5:14b-instruct
python -m chirox.cli debrief
```

Expected local-model proof:

- If Ollama and the model are available, Chirox speaks only from recorded
  evidence.
- If Ollama or the model is unavailable, Chirox reports the failure instead of
  inventing a debrief.

## Optional Wisdom Proof

The wisdom corpus is public-domain text. If the local files are missing,
`chirox sage` attempts to fetch them.

```powershell
python -m chirox.cli sage --topic discipline --answer "I showed up honestly today."
python -m chirox.cli growth
python -m chirox.cli verify
```

Expected wisdom proof:

- `sage` grounds the dialogue in the wisdom corpus and seals the exchange.
- `growth` summarizes sealed wisdom dialogues.
- `verify` still reports an intact Codex chain.

## Public Governance Proof

Inspect the public guardrails:

```powershell
Get-Content CONTRIBUTING.md
Get-Content SECURITY.md
Get-Content PRIVACY.md
Get-Content TRUTH_AUDIT.md
Get-Content CURRICULUM_MAP.md
Get-Content HARDWARE_WITNESS_PROTOCOL.md
```

Expected governance proof:

- contribution rules forbid false authority, paid-course copying, and overstated
  Chirox claims.
- security and privacy docs keep Dojo data, camera media, voice data, models,
  and local records private by default.
- truth audit separates proven, hardware-witnessed, gated, measurable,
  record-only, and deferred surfaces.
- hardware witness protocol names the exact remaining gates.

## Hardware-Gated Vision Proof

This path needs a working camera and a person in frame. It is not proven by
terminal optimism.

```powershell
python -m chirox.cli vision --source 0 --seconds 10 --no-show
```

Expected hardware proof:

- The command emits JSON.
- If a body is detected, the output includes deterministic stance measurements
  and explicit uncertainty.
- If no body is detected, the output must say so plainly.
- Generative AI does not assess physical form.

## Visual Timeline Proof

This records a short local session into the private, git-ignored `Dojo/media/`
archive and seals a manifest into the Dojo Record.

```powershell
python -m chirox.cli record --exercise horse_stance --source 0 --seconds 10 --no-show
python -m chirox.cli timeline
python -m chirox.cli verify
```

Expected timeline proof:

- `record` writes a local video archive file and emits a manifest.
- `timeline` lists sealed recordings oldest-first.
- `verify` still reports an intact Codex chain.

## What Does Not Count

- A passing test suite does not prove a live camera run.
- A synthetic fixture does not prove the physical rig.
- A model response does not prove body truth.
- A README claim does not prove software behavior.

Proof means code ran, output existed, limitations were visible, and the result
was inspected.
