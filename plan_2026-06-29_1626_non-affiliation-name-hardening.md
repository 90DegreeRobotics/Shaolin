# Plan: Non-Affiliation Name Hardening — 2026-06-29 16:26

## Status
IN-PROGRESS

## Goal
Add Master Shi Heng Yi and Shaolin Temple Europe explicitly to the README non-affiliation sentence for maximum clarity.

## Context
- Files that will be read:
  - `README.md`
- Files that will be edited:
  - `README.md`
  - `plan_2026-06-29_1626_non-affiliation-name-hardening.md`
- Preconditions:
  - The broader access statement already exists in `ACCESS_AND_INSPIRATION.md`.
  - This is a wording hardening only.

## Steps

### Step 1 — Patch README
- [x] Action: Add explicit names to the non-affiliation sentence.
- Files touched:
  - `README.md`
- Expected outcome:
  - The top-level disclaimer names Master Shi Heng Yi and Shaolin Temple Europe directly.

### Step 2 — Verify wording
- [x] Action: Search README for the updated sentence.
- Files touched:
  - none
- Expected outcome:
  - The exact names are present.

### Step 3 — Commit and push
- [ ] Action: Stage explicit files, commit, and push to `origin/main`.
- Files touched:
  - git index/history
- Expected outcome:
  - The hardening patch is public.

### Step 4 — Close plan
- [ ] Action: Mark plan `COMPLETED`, commit closure, and push.
- Files touched:
  - `plan_2026-06-29_1626_non-affiliation-name-hardening.md`
- Expected outcome:
  - The plan accurately records completion.

## Test gate

```pwsh
Select-String -LiteralPath 'C:\Shaolin\README.md' -Pattern 'Master Shi Heng Yi|Shaolin Temple Europe|not affiliated'
git status -sb
git log -1 --oneline
git ls-remote --heads origin main
```

## Rollback
Do not delete or rewrite. Correct forward if wording needs adjustment.
