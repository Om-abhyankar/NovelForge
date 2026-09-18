# Contributing to NovelForge

NovelForge is a one-person hobby project, built entirely through AI pairing
rather than hand-written line by line — see `CLAUDE.md` if that's the part
you're curious about. That doesn't mean contributions aren't welcome; it
means the bar for "does this actually work" is real code review and real
testing, the same as any other project.

## The most useful thing you can do

**Open an issue.** Bug reports, confusing behaviour, a feature you wish
existed, a framework or check you think is missing — all of it is useful,
even if you never touch the code yourself. Include:

- What you did, and what you expected to happen instead of what did.
- Windows version, and whether you're running from `Write.bat` or a shell.
- If it's a crash: whatever the error dialog or console printed.

## If you want to submit code

1. Fork the repo and branch from `main`.
2. Keep the change scoped — one fix or one feature per pull request, not a
   grab-bag. It's much easier to review and much easier to revert if
   something's wrong with just one part of it.
3. There is currently no automated test suite (see `CLAUDE.md` for why, and
   for what a good first one would cover). Until there is, describe how you
   tested the change by hand in the PR description.
4. Follow the two rules that already shape this codebase:
   - Every window must fit any screen/DPI scaling — use `center_window()`
     in `novelforge/ui/widgets.py`, never call `.geometry()` directly.
   - `.docx` files are the source of truth; `project.json` holds only
     metadata (ordering, links, word counts). Never put prose there.
5. Open the pull request against `main` and describe what changed and why.

## Code of conduct

Be someone it's pleasant to get a bug report from. See `CODE_OF_CONDUCT.md`.
