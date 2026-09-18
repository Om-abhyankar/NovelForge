# Working on NovelForge

This file is for whoever (human or AI) touches this code next. Read it before
changing anything — it exists because this whole project has been built by AI
pairing with a non-programmer, one conversation at a time, and every session
starts cold. The only continuity is what got written down. If you learn
something the next session would need, add it here instead of only saying it
in chat.

## What this is

NovelForge is a local-first novel-writing studio: character sheets, outline
frameworks, a timeline, a "story graph" that mines your prose for entities, a
fantasy map maker, diagnostics, and a compiler — all reading and writing real
`.docx` files on disk, no account, no cloud. See `README.md` for the
user-facing tour. This file is the developer-facing one.

**The user is a writer, not a programmer.** They cannot read a traceback and
decide what it means. "It's glitchy" or "it doesn't feel right" is a complete
and valid bug report — the job is to find the actual mechanism yourself, not
to ask them to narrow it down technically.

## Two codebases live here — only one is real

- **`novelforge/`** — Python 3.13 + Tkinter. **This is the whole product.**
  Launched by `Write.bat` → `python -m novelforge`. Creating a novel, writing,
  the map maker, the corkboard, the outline, the timeline, every settings
  dialog, compiling, backups — all of it lives here and all of it works.
- **`web/`** — Next.js 15 + React 19, static-exported so end users only ever
  need Python. This is an **unfinished redesign**, reachable only via
  `python -m novelforge --web`. Its shell, settings screen and editor are
  wired to the engine; the maps, dashboard, library, character and world
  screens **do not exist yet**. Do not treat anything in `web/` as the
  current app, and do not assume a feature exists there just because it
  exists in `novelforge/ui/`.

If a future session's goal is to finish migrating `novelforge/ui/` to
`web/`, that's a real, large, deliberate project — confirm with the user
before starting it, don't drift into it while fixing something else.

## Module map (`novelforge/`)

The engine (no UI toolkit imports — this is what `web/` will eventually sit
on top of too):

| Module | What it owns |
|---|---|
| `model.py` | The project data model — everything that isn't prose text |
| `project.py` | Create/open/save a project; keeps `project.json` in step with disk |
| `docxio.py` | Reading and writing the two shapes of `.docx` this tool produces |
| `atomic.py` | Crash-safe, OneDrive-safe file writing (write-temp-then-replace) |
| `backup.py` | Snapshots and verified `.zip` backups |
| `recovery.py` | Crash recovery / "where was I" |
| `undo.py` | Undo/redo for everything that isn't typing (Tk's Text widget handles typing itself) |
| `compiler.py` | Assembles every scene into one manuscript-format document |
| `diagnostics.py` | Offline heuristic prose/developmental editing checks |
| `grammar.py` | Spelling/grammar without shipping a dictionary file |
| `lexicon.py` | The editor's own vocabulary — names, invented words — learned from the project |
| `stats.py` | Sessions, streaks, pace, deadline projection |
| `structures.py` | The nine outline frameworks, as data |
| `templates.py` | The field lists behind every generated `.docx` reference sheet |
| `storygraph.py` | Mines the manuscript for entities/mentions and builds the relationship graph |
| `mapgen.py` | Procedural world generation (heightmap → coastline → rivers → settlements → names) |
| `mapmaker.py` | Map data model + `build_primitives()`, the single source of truth rendered by the editor, PNG export and SVG export |
| `mapstory.py` | Where the map connects back to Locations/the story graph |
| `config.py` | App paths and the one settings JSON file |
| `server.py` | Local-only HTTP bridge (binds `127.0.0.1`) used by `--web`/`--serve` |
| `desktop.py` | pywebview shell around the server, for `--web` |

The UI (`novelforge/ui/`), Tkinter, all of it live:

| Module | What it owns |
|---|---|
| `app.py` | Main window: binder / editor / inspector, ~3800 lines, the hub everything else is opened from |
| `mapeditor.py` | The map maker window — canvas UI over `mapmaker`'s primitive list |
| `corkboard.py` | Corkboard and the character-relationship web, two canvas views |
| `storyviews.py` | The four story-graph windows |
| `writing.py` | Editor intelligence: completion, live spelling/grammar marks |
| `dialogs.py` | Modal `Dialog` subclasses and non-modal tool windows |
| `widgets.py` | Small reusable widgets, incl. `center_window()` (see rule below) |

**There is no `ui/theme.py` any more.** A ~600-line second design system
(WCAG-contrast-checked palettes, sv-ttk integration, elevation-based
surfaces) lived there but was never imported by anything — `config.py`'s
much simpler `theme()` dict (`bg`/`fg`/`panel`/`accent`, per theme name) is
and always was the one actually driving every widget. It was removed on
2026-09-18 after confirming zero call sites anywhere in the repo. If a
future session wants the richer palette, it existed in git history before
that date — but wiring an app-wide theme swap in blind, with no way to
visually check a Tkinter canvas from here and no test suite, is a real risk;
don't do it without actually running the app and looking at it, ideally with
the user watching.

## Rules that are load-bearing, not style preference

**1. `.docx` is the truth; `project.json` is only metadata.** Ordering,
links, word counts, targets — never prose. This was a deliberate reversal of
the original plain-markdown blueprint, kept because OOXML is an open ISO
standard. Don't add a second place prose can live.

**2. Every window must fit the screen it opens on**, at any resolution or
Windows display scaling — see `README.md`'s "A rule for anyone changing this
code". Size windows through `center_window()` in `widgets.py`; never call
`.geometry()` directly. **Caveat:** the README says this is "enforced by a
test that opens all 23 windows at six resolutions" — as of this writing
**no such test file exists anywhere in the repo or its git history.** Either
that test was run ad hoc in a past session and never committed, or the claim
is aspirational. Don't trust it as a safety net; if you touch window sizing,
check by hand, and consider actually writing and committing that test.

**3. Speed over polish, always.** The user's own words: *"make it work
amazing, no lags, super fast... I dont care of any fancy ui but make it
workable and user friendly."* Concretely:
   - Rendering never opens a `.docx` — every number the UI shows comes from
     `project.json`.
   - Debounce on idle, never do work per keystroke (autosave 30s idle, word
     recount 400ms).
   - Anything touching many files is an explicit menu command wrapped in
     `App._busy()`, never automatic or on a timer.
   - **On any Tkinter Canvas view** (`mapeditor.py`, `corkboard.py`): a full
     redraw (`canvas.delete("all")` + rebuild every item) is fine for a
     discrete action, but must never run synchronously off a
     `<Motion>`/`<B1-Motion>`-class event, which can fire dozens of times a
     second. Either debounce it (`after(16, redraw)`, coalescing to one
     frame — see `_schedule_redraw()` in `mapeditor.py`) or, better, mutate
     existing canvas items in place (`canvas.move(...)`, `canvas.coords(...)`)
     instead of rebuilding. **This exact mistake was the map maker's
     "glitchy" panning/dragging** — `_on_drag` and `_on_middle_drag` were
     calling a full synchronous `redraw()` on every pan motion event, which
     also recomputed pin-label collision placement (`layout_pin_labels`,
     roughly O(pins × placed)) from scratch every time, even though panning
     changes nothing about the map itself. Fixed by (a) panning via
     `canvas.move("all", dx, dy)` instead of a rebuild, and (b) caching
     `layout_pin_labels`'s result on the `GameMap` (`_label_cache`),
     invalidated by a content fingerprint, so a redraw triggered by
     view-only changes (pan/zoom) reuses it instead of recomputing it. If
     you build another canvas-based view, apply this from the start rather
     than rediscovering it.

**4. No hard-coded colours, radii, shadows or fonts outside the theme
tokens** in `ui/theme.py`. Three themes exist as separate designs, not
inversions of each other (per the design-system notes — dark, light, sepia).

## There is no automated test suite for `novelforge/`

Despite comments/README text implying one exists (see rule #2's caveat),
`git log --all` shows no test file was ever committed. At minimum, before
calling a change done: `python -m py_compile` the files you touched, and
where practical exercise the changed function directly (e.g. via a throwaway
`python -c "..."` import, as done for `mapmaker.py`'s label cache during the
2026-09 map-performance fix) rather than trusting it by inspection alone.
Building a real, committed `pytest` suite — starting with the window-fit
check the README already claims exists — would be a good, scoped project for
a future session; ask before taking it on, since it's a meaningful chunk of
work on its own.

`web/` does have real automated checks: `npm run test` in `web/` runs
typecheck + lint + format-check, and `npm run shots` (Playwright, via
`web/scripts/shoot.mjs`) screenshots every theme — genuinely useful for
catching visual regressions in the parts of `web/` that exist.

## If you drive the real GUI to test it: this bit nearly wrote real user data

There's no harness for this, so a 2026-09 session built one: seed a
throwaway `Project.create()`, point `NOVELFORGE_SETTINGS` at a matching
throwaway settings file, launch the real `App()`, walk the menu tree calling
each command's Tcl name directly (`app.tk.call(cmd_name)` — exactly what a
real click does), and screenshot anything that opens via
`PIL.ImageGrab.grab()`. This is genuinely useful and caught a real bug (see
the map-toolbar entry below) — but it went wrong twice against the user's
**real** project before working safely, both times because the walker
doesn't know which menu entries are safe to invoke blindly:

1. **A shell/path timing bug**, not the app's fault: writing the throwaway
   settings file *after* something has already imported `novelforge.config`
   does nothing, because `config.settings = Settings()` is a module-level
   singleton read once at import time. `NOVELFORGE_SETTINGS` must point at a
   file that already has the right content *before the first
   `import novelforge...` of the process* - write it in a separate earlier
   process/step, not inline before constructing `App()` in the same one. Git
   Bash also silently rewrites `/tmp/...`-style paths differently depending
   on how they cross into a native `python.exe`'s environment - use
   PowerShell with explicit `C:\...` paths for this, not Bash, and keep the
   test project shallow (`C:\something`, not nested deep under a scratch
   directory) or `zipfile`/`docx` writes fail on Windows' ~260-char path
   limit.
2. **The real hazard, and not a bug in the app**: walking *every* menu entry
   blindly, including cascades, invoked `File > Open Recent > <the user's
   actual novel>` exactly as a real click would - which correctly switched
   the live app to it - and then correctly ran every later Manuscript/Tools
   command (compile, write outline, back up, write story bible...) against
   *that* project for the rest of the walk. A second run also walked into
   `Plan > Story Structure > <a framework>`, which correctly switched the
   real project's active outline framework. Both were the app working
   exactly as designed; the bug was testing methodology treating a
   real-data-backed cascade the same as a static one. Recovery both times
   was: diff `project.json` against the automatically-kept `project.json.bak`
   to see exactly what changed, delete anything the walk generated fresh
   (compared file *creation* time to *modified* time - equal means the file
   didn't exist before), and restore `project.json` from `.bak` if a setting
   actually changed.

**If you do this again:** assert the loaded project's title matches the
throwaway one immediately after `App()` starts, before invoking anything,
and abort loudly if it doesn't. Skip `Open Recent` and `Story Structure`
(and treat any other cascade backed by real persisted state the same way)
rather than walking into them. Everything else — the ~80 ordinary commands —
walked cleanly with zero exceptions across two full runs, which is a decent
amount of real confidence for an app with no test suite.

## Menu organisation (as of 2026-09)

Two deliberate moves, made after actually walking every menu command and
looking at where things sat: **Find in Project / Find and Replace moved
from Tools to Edit** (every other app the user has ever used puts them
there), and **Write Story Bible moved from Plan to Manuscript**, next to
Write Outline.docx / Write Reverse Outline — all three are the same kind of
action (turn what's already in the project into a reference document), so
Manuscript is now consistently "things this generates" and Plan is
consistently "things you look at or fill in on screen." `README.md` was
updated to match (`Plan → Write Story Bible` → `Manuscript → Write Story
Bible`); it also had a pre-existing, unrelated error calling Write Reverse
Outline a Tools command when it was always under Manuscript - fixed too.
If you reorganise a menu again, grep the README for the old `"X → Y"`
phrasing first; it's prose, not generated from the menu code, so nothing
catches this automatically.

## Map maker: what already exists (check before "adding" it again)

The map maker is more built-out than a quick skim of `README.md` suggests
(the README's "Maps" section predates the two most recent map commits and
undersells current features). Before proposing an addition, confirm it
isn't already here:

- Procedural world generation (`mapgen.py`): heightmap via fractal value
  noise → coastline extraction → **downhill-flow rivers** (not just noise) →
  biome placement → habitability-scored settlement placement → roads.
- One-press **"Surprise Me"** (full random world from OS entropy, seed
  recorded for reproducibility) alongside a parameterised **"Generate..."**
  dialog.
- Per-culture procedural naming with **user-editable name lists**
  (`Name Styles.json` in the project's Maps folder, "Edit Names" in the UI),
  and **per-role styles** — settlements, realms, regions, seas and rivers can
  each sound different, or be pointed at the same style.
  Settlement-name collisions are disambiguated (Upper/Lower/Little/Great/...,
  then a numeral) rather than left blank.
  - **Greedy label-collision avoidance** for every pin/label
    (`layout_pin_labels` in `mapmaker.py`), with a documented fallback of
    hiding a name rather than printing it on top of another.
  - **Pins link to Location sheets** — right-click → Link, double-click to
    open the linked sheet in Word.
  - **Layers**, shown/hidden independently.
  - One shared primitive list (`build_primitives()`) rendered identically by
    the Tkinter canvas, the PNG exporter, and the SVG exporter — "what you
    see while editing is exactly what you export." Keep it that way; don't
    let PNG/SVG export drift into their own drawing logic.

**Genuine gaps**, worth considering later rather than assumed to already
exist: coastlines come from smoothed noise rather than a Voronoi/Delaunay
mesh, so they read as smooth rather than jagged/geologic (Azgaar's Fantasy
Map Generator, MIT-licensed, is the reference implementation if this is ever
worth the rewrite risk — it is a genuine rewrite of `mapgen.py`'s terrain
step, not a small change); there's no "zoom into a town" street-layout
generator (Watabou's TownGeneratorOS is the reference); and the hand-draw
tools have no click-to-stamp icon brush (mountain/tree/castle) — freehand and
click-to-place-points are the only ways to draw terrain by hand.

**Toolbar button widths must fit their own label.** The main toolbar's
buttons used one flat `width=8` for every label, which clipped "Surprise Me"
and "Edit Names" to "Surprise !" and "Edit Nam" — invisible from reading the
code, only visible in an actual screenshot. Fixed (2026-09) to
`width=max(8, len(label) + 1)` per button. Don't "fix" this by removing
`width=` entirely — with this many buttons in one un-wrapped row, letting
ttk pad every button to its natural size pushes the whole toolbar past the
window's edge and hides "Help" and the coordinate readout off-screen
instead, which is worse and easy to miss since nothing raises an exception.

## Security posture

Reviewed 2026-09, manually — the `security-review` skill's own frontmatter
shells out to `git diff origin/HEAD...`, which fails outright since this
repo has no remote configured. Don't rely on that skill here until one
exists.

The threat model is deliberately small: single local user, no accounts, no
outbound network calls anywhere in `novelforge/`, and the one local server
(`server.py`, used only by the unfinished `--web`/`--serve` path) binds
`127.0.0.1` with a fresh random per-launch token required on every route
except `/api/health`. Within that model:

- **Fixed already**: `backup.py`'s zip-extraction path-traversal guard was
  a plain string `startswith`, which a sibling folder name (`"MyBook2"`
  starting with `"MyBook"`) could satisfy without actually being inside the
  destination - now checks `resolved == dest or dest in resolved.parents`.
  `config.py`'s "Reveal in Explorer" built a shell string via `os.system`
  from a raw path - now `subprocess.Popen` with an argument list, no shell.
- **Checked and clean**: no `eval`/`exec`/`pickle`/`os.system`/`shell=True`
  anywhere else in the codebase. The only other `zipfile.ZipFile(...,
  "r")` usages (`atomic.py`, `backup.py`'s `verify_backup`) only read
  metadata (`testzip`/`namelist`), never `extractall`. `server.py`'s static
  file server already had the *correct* traversal guard
  (`target.relative_to(WEB_ROOT.resolve())`) from the start - a good
  reference for what backup.py's guard should have looked like. No CORS
  headers are set anywhere, so the loopback server doesn't opt into
  cross-origin access even accidentally.
- **Not a bug, just worth knowing**: unhandled exceptions in any `/api/`
  route get their traceback echoed back in the JSON response
  (`server.py`'s `_api`). Harmless given the threat model (loopback-only,
  token-gated, single local user) and actually useful for debugging the
  unfinished web UI - just don't assume this is safe if `server.py` is ever
  exposed beyond loopback.

## Running it

```
Write.bat                          # the real app (Tkinter)
python -m novelforge                # same, from a shell
python -m novelforge --web          # incomplete web redesign - do not use for real writing
python -m novelforge --serve        # local server only, prints the URL
pip install python-docx Pillow      # the only two non-stdlib deps for novelforge/
```

`web/` (only if working on the redesign itself):
```
cd web
npm install
npm run dev      # localhost:4321
npm run build     # static export into web/out/, committed to the repo -
                   # this is what lets end users skip Node entirely
npm run test      # typecheck + lint + format check
```
