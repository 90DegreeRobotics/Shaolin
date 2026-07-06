# CLAUDE.md — working rules for this repository

## The Main-Only Law (no exceptions)

- There is ONE branch: `main`. Never create another branch, locally or on the
  remote. No feature branches, no worktree branches, no experiment branches.
- ALL work is committed, staged, and pushed to `origin/main` before a task ends.
  Never leave uncommitted changes, stashes, or local-only commits behind.
- If the remote has moved, sync with `git pull --rebase --autostash`, re-run the
  test suite, then push. The laptop and `origin/main` must end every session
  identical.
- Run the full test suite (`python -m pytest tests`) before every push. A red
  suite blocks the push — fix it first.

## Other standing rules

- Commit messages follow the existing conventional style:
  `feat(chirox): …`, `docs(temple): …`, `chore(repo): …`.
- The Dojo Record and everything under `Dojo/` is private runtime data and is
  git-ignored — never commit it, never loosen `.gitignore` around it.
- The practitioner does not use a CLI: every new capability must be reachable
  from the web cockpit and/or by voice, not only by command.
- STATUS.md records only what is built AND verified; claims must stay honest.
