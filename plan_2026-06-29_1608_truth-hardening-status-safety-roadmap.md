# Plan: Truth Hardening, Safety, Roadmap — 2026-06-29 16:08

## Status
IN-PROGRESS

## Goal
Harden the public Shaolin repository after review: make current implementation status explicit, pull safety doctrine into a visible file, add a roadmap, add a license notice, add a non-affiliation disclaimer, and move older scaffold documents into an archive/supporting-drafts lane without deleting content.

## Context
- Relevant documents:
  - `README.md`
  - `1yeartoShaolin.md`
  - `Chirox_Integration_Plan.md`
  - `first_30_days.md`
  - `Self_Mastery_Plan.md`
  - `Shaolin_Lifestyle_Guide.md`
  - `Mandarin/`
- Files that will be read:
  - `README.md`
  - `1yeartoShaolin.md`
  - older scaffold docs
- Files that will be edited or created:
  - `README.md`
  - `STATUS.md`
  - `SAFETY.md`
  - `ROADMAP.md`
  - `LICENSE.md`
  - `Archive/README.md`
  - archived scaffold doc paths via `git mv`
  - this plan document
- Preconditions / dependencies:
  - `origin/main` is current at the start of the task.
  - `Dojo/` and `plan.txt` are untracked and outside this scope.
  - License choice is grounded in official Creative Commons BY-SA 4.0 and OSI MIT references.

## Steps

### Step 1 — Add truth and safety files
- [x] Action: Create `STATUS.md`, `SAFETY.md`, and `ROADMAP.md`.
- Files touched:
  - `STATUS.md`
  - `SAFETY.md`
  - `ROADMAP.md`
- Expected outcome:
  - Public readers can see what exists, what is concept only, and what safety rules govern the practice.

### Step 2 — Add license notice
- [x] Action: Create `LICENSE.md` with documentation licensed under CC BY-SA 4.0 and future software under MIT unless noted otherwise.
- Files touched:
  - `LICENSE.md`
- Expected outcome:
  - Public sharing intent has a clear legal surface.

### Step 3 — Archive older scaffolds by move, not deletion
- [x] Action: Create `Archive/README.md` and move older scaffold documents into `Archive/Supporting_Drafts/` using content-preserving moves.
- Files touched:
  - `Archive/README.md`
  - `Archive/Supporting_Drafts/first_30_days.md`
  - `Archive/Supporting_Drafts/Self_Mastery_Plan.md`
  - `Archive/Supporting_Drafts/Shaolin_Lifestyle_Guide.md`
- Expected outcome:
  - Older documents remain available but no longer compete with the current manual.

### Step 4 — Update README front gate
- [x] Action: Add non-affiliation disclaimer, status/safety/roadmap/license links, and update document list for archived scaffolds.
- Files touched:
  - `README.md`
- Expected outcome:
  - The front page states the repo is unaffiliated with Shaolin Temple, manual-first, and not yet a software implementation.

### Step 5 — Verify content and links
- [x] Action: Read/search the updated files and check git status.
- Files touched:
  - none
- Expected outcome:
  - Status, safety, roadmap, license, disclaimer, and archive labels are present.

### Step 6 — Commit and push
- [ ] Action: Stage explicit files, commit, and push to `origin/main`.
- Files touched:
  - git index/history
- Expected outcome:
  - The public repo is hardened on `origin/main`.

### Step 7 — Close the plan
- [ ] Action: Mark this plan `COMPLETED`, commit the closure, and push.
- Files touched:
  - `plan_2026-06-29_1608_truth-hardening-status-safety-roadmap.md`
- Expected outcome:
  - The plan accurately records completion.

## Test gate
Commands to run to verify success:

```pwsh
Select-String -LiteralPath 'C:\Shaolin\README.md','C:\Shaolin\STATUS.md','C:\Shaolin\SAFETY.md','C:\Shaolin\ROADMAP.md','C:\Shaolin\LICENSE.md' -Pattern 'not affiliated|No physical-assessment code|concept|Green|Yellow|Red|CC BY-SA|MIT'
Get-ChildItem -LiteralPath 'C:\Shaolin\Archive\Supporting_Drafts'
git status -sb
git log -1 --oneline
git ls-remote --heads origin main
```

## Rollback
Do not delete or rewrite history. If a label or license statement is wrong, make a forward correction commit.

## Next-agent pickup
If Status is INTERRUPTED, the next agent should:
1. Read this plan.
2. Run `git status -sb`.
3. Continue from the first unchecked step.
