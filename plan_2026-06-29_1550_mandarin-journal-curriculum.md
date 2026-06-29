# Plan: Mandarin Journal Curriculum — 2026-06-29 15:50

## Status
COMPLETED

## Goal
Add the pencil-journal method to the main Shaolin manual and create a repository section for learning Mandarin with open-source or openly available resources. The new section should include a syllabus, curriculum, journaling method, and resource map.

## Context
- Relevant documents:
  - `README.md`
  - `1yeartoShaolin.md`
- Files that will be read:
  - `README.md`
  - `1yeartoShaolin.md`
- Files that will be edited:
  - `README.md`
  - `1yeartoShaolin.md`
  - `Mandarin/README.md`
  - `Mandarin/JOURNALING_METHOD.md`
  - `Mandarin/SYLLABUS.md`
  - `Mandarin/CURRICULUM.md`
  - `Mandarin/RESOURCES.md`
  - `plan_2026-06-29_1550_mandarin-journal-curriculum.md`
- Preconditions / dependencies:
  - The repository already has `origin/main` and public README custody.
  - Existing untracked `Dojo/` and `plan.txt` are outside this scope and will not be staged.
  - Resource claims should be grounded in checked public source pages.

## Steps

### Step 1 — Add the journaling method to the main manual
- [x] Action: Add a section explaining English thought -> Mandarin distillation -> calligraphy practice as an evening Dojo Record method.
- Files touched:
  - `1yeartoShaolin.md`
- Expected outcome:
  - The manual gives a clear daily paper-and-pencil ritual without making journaling bloated.

### Step 2 — Create Mandarin learning section
- [x] Action: Create the `Mandarin/` folder with entrypoint, journaling method, syllabus, curriculum, and resources.
- Files touched:
  - `Mandarin/README.md`
  - `Mandarin/JOURNALING_METHOD.md`
  - `Mandarin/SYLLABUS.md`
  - `Mandarin/CURRICULUM.md`
  - `Mandarin/RESOURCES.md`
- Expected outcome:
  - The repo has a beginner-safe Mandarin learning system connected to the Shaolin practice.

### Step 3 — Update root README
- [x] Action: Link the Mandarin section and identify it as an open-source learning lane.
- Files touched:
  - `README.md`
- Expected outcome:
  - A public reader can find the Mandarin syllabus from the front page.

### Step 4 — Verify content
- [x] Action: Read the new and edited Markdown files and search for key phrases.
- Files touched:
  - none
- Expected outcome:
  - The section exists, links are present, and the journaling method is discoverable.

### Step 5 — Commit and push
- [x] Action: Stage explicit files, commit, and push to `origin/main`.
- Files touched:
  - git index/history
- Expected outcome:
  - The public repo contains the Mandarin and journaling system.

### Step 6 — Close the plan
- [x] Action: Mark this plan `COMPLETED`, commit the plan closure, and push.
- Files touched:
  - `plan_2026-06-29_1550_mandarin-journal-curriculum.md`
- Expected outcome:
  - The plan accurately records completion.

## Test gate
Commands to run to verify success:

```pwsh
Get-ChildItem -LiteralPath 'C:\Shaolin\Mandarin'
Select-String -LiteralPath 'C:\Shaolin\1yeartoShaolin.md','C:\Shaolin\README.md','C:\Shaolin\Mandarin\*.md' -Pattern 'English thought|Mandarin|calligraphy|syllabus|curriculum|open-source'
git status -sb
git log -1 --oneline
git ls-remote --heads origin main
```

## Rollback
Do not delete. If wording or structure is wrong, make a forward correction commit.

## Next-agent pickup
If Status is INTERRUPTED, the next agent should:
1. Read this plan.
2. Run `git status -sb`.
3. Continue from the first unchecked step.
