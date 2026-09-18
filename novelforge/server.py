"""
The local bridge between the Python engine and the interface.

This is NOT an internet service. It binds to 127.0.0.1 - the loopback address,
which the operating system will not route off the machine - on a port chosen at
random each launch. Nothing can reach it from outside this computer, there are
no accounts, no keys and no outbound requests. It exists only so the two halves
of one program can talk to each other.

Standard library only, deliberately: every extra dependency is one more thing
that can fail to install on somebody else's laptop.
"""

from __future__ import annotations

import json
import mimetypes
import secrets
import socket
import threading
import traceback
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import unquote, urlparse

from . import APP_VERSION
from .config import FOLDERS, open_in_default_app, projects_root, reveal_in_explorer, settings
from .project import Project, ProjectError, list_projects

# Serving from the package directory means a frozen build finds it too.
WEB_ROOT = Path(__file__).resolve().parent / "web"

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("image/svg+xml", ".svg")


class ApiError(Exception):
    """A failure with a status code, so handlers can just raise."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


class State:
    """
    Everything the server knows.

    A single lock guards the open project: two requests arriving together must
    not both mutate the manifest.
    """

    def __init__(self) -> None:
        self.project: Optional[Project] = None
        self.lock = threading.RLock()
        # A shared secret every request must present. Even on loopback, another
        # program on this machine could otherwise poke at the API.
        self.token = secrets.token_urlsafe(24)

    def require(self) -> Project:
        if self.project is None:
            raise ApiError("No novel is open.", 409)
        return self.project


STATE = State()


# ==========================================================================
# Routes
# ==========================================================================

Handler = Callable[[Dict[str, Any]], Any]
ROUTES: Dict[Tuple[str, str], Handler] = {}


def route(method: str, path: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        ROUTES[(method, path)] = fn
        return fn

    return register


# -- meta ------------------------------------------------------------------


@route("GET", "/api/health")
def _health(_body: Dict[str, Any]) -> Any:
    return {
        "ok": True,
        "version": APP_VERSION,
        "hasProject": STATE.project is not None,
    }


@route("GET", "/api/settings")
def _get_settings(_body: Dict[str, Any]) -> Any:
    return settings.as_dict()


@route("POST", "/api/settings")
def _set_settings(body: Dict[str, Any]) -> Any:
    values = body.get("values")
    if not isinstance(values, dict):
        raise ApiError("Expected a 'values' object.")
    settings.update(values)
    return settings.as_dict()


# -- library ---------------------------------------------------------------


@route("GET", "/api/library")
def _library(_body: Dict[str, Any]) -> Any:
    out = []
    for title, path in list_projects():
        manifest = path / "project.json"
        words = 0
        modified = ""
        genre = ""
        try:
            raw = json.loads(manifest.read_text(encoding="utf-8"))
            words = sum(int(s.get("word_count") or 0)
                        for s in raw.get("scenes") or [])
            modified = str(raw.get("modified") or "")
            genre = str(raw.get("genre") or "")
            target = int((raw.get("targets") or {}).get("total_words") or 0)
        except Exception:
            target = 0
        cover = next(
            (str(c.name) for c in path.glob("cover.*")
             if c.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}),
            "",
        )
        out.append({
            "title": title,
            "path": str(path),
            "words": words,
            "target": target,
            "genre": genre,
            "modified": modified,
            "cover": cover,
        })
    return {"projects": out, "root": str(projects_root())}


def _save_outgoing_project() -> None:
    """
    Save whatever project is currently open, before switching away from it.

    A scene's synopsis, its goal/conflict/disaster fields, idea-inbox
    entries, links - anything that lives in project.json rather than a
    .docx - has no second copy anywhere. Swallowing a save failure here and
    switching anyway (the previous behaviour) meant a locked manifest file
    (OneDrive mid-sync, a permissions error) silently dropped whatever of
    that metadata had not been saved yet, with no error and no sign anything
    was wrong. Raising instead means the switch itself fails and the outgoing
    project is left exactly as it was, unsaved, until the problem is fixed.
    """
    if STATE.project is None:
        return
    try:
        STATE.project.save()
    except Exception as exc:
        raise ApiError(
            f"Could not save '{STATE.project.data.title}' before switching "
            f"projects: {exc}. Nothing has been changed - fix the problem "
            f"and try again.", 409,
        ) from exc


@route("POST", "/api/project/open")
def _open(body: Dict[str, Any]) -> Any:
    path = str(body.get("path") or "").strip()
    if not path:
        raise ApiError("A folder path is required.")
    with STATE.lock:
        _save_outgoing_project()
        try:
            STATE.project = Project.open(Path(path))
        except (ProjectError, OSError) as exc:
            raise ApiError(str(exc), 404) from exc
        STATE.project.sync_from_disk()
        settings["last_project"] = path
        return _project_payload(STATE.project)


@route("POST", "/api/project/create")
def _create(body: Dict[str, Any]) -> Any:
    title = str(body.get("title") or "").strip()
    if not title:
        raise ApiError("A title is required.")
    with STATE.lock:
        _save_outgoing_project()
        try:
            project = Project.create(
                title=title,
                author=str(body.get("author") or ""),
                genre=str(body.get("genre") or ""),
                structure=str(body.get("structure") or "three_act"),
                target_words=int(body.get("targetWords") or 90000),
                daily_words=int(body.get("dailyWords") or 1000),
                deadline=str(body.get("deadline") or ""),
                packs=body.get("packs") or [],
            )
        except (ProjectError, OSError) as exc:
            raise ApiError(str(exc)) from exc
        STATE.project = project
        settings["last_project"] = str(project.root)
        return _project_payload(project)


@route("GET", "/api/project")
def _project(_body: Dict[str, Any]) -> Any:
    with STATE.lock:
        return _project_payload(STATE.require())


@route("POST", "/api/project/save")
def _save(_body: Dict[str, Any]) -> Any:
    with STATE.lock:
        project = STATE.require()
        project.save(force=True)
        return {"ok": True, "words": project.data.word_count}


@route("POST", "/api/project/sync")
def _sync(body: Dict[str, Any]) -> Any:
    with STATE.lock:
        project = STATE.require()
        scenes, entities = project.sync_from_disk(force=bool(body.get("force")))
        return {"scenes": scenes, "entities": entities,
                **_project_payload(project)}


def _project_payload(project: Project) -> Dict[str, Any]:
    from . import stats

    data = project.data
    projection = stats.Projection(data)
    return {
        "root": str(project.root),
        "title": data.title,
        "author": data.author,
        "genre": data.genre,
        "logline": data.logline,
        "structure": data.structure,
        "words": data.word_count,
        "targets": {
            "total": data.targets.total_words,
            "daily": data.targets.daily_words,
            "deadline": data.targets.deadline,
        },
        "progress": {
            "percent": projection.percent,
            "remaining": projection.remaining,
            "average": projection.average,
            "daysLeft": projection.days_left,
            "requiredDaily": projection.required_daily,
            "onTrack": projection.on_track,
            "streak": stats.streak(data),
            "bestStreak": stats.best_streak(data),
            "sparkline": [
                v for v in _daily_series(data, 30)
            ],
        },
        "chapters": [
            {
                "id": c.id, "title": c.title, "order": c.order,
                "status": c.status, "include": c.include_in_compile,
                "synopsis": c.synopsis,
                "scenes": [
                    {
                        "id": s.id, "title": s.title, "order": s.order,
                        "synopsis": s.synopsis, "status": s.status,
                        "type": s.scene_type, "words": s.word_count,
                        "target": s.target_words, "include": s.include_in_compile,
                        "povId": s.pov_id, "characterIds": s.character_ids,
                        "locationIds": s.location_ids, "threadIds": s.thread_ids,
                        "goal": s.goal, "conflict": s.conflict,
                        "disaster": s.disaster, "reaction": s.reaction,
                        "dilemma": s.dilemma, "decision": s.decision,
                        "valueStart": s.value_start, "valueEnd": s.value_end,
                        "storyDate": s.story_date, "notes": s.notes,
                    }
                    for s in data.scenes_in(c.id)
                ],
            }
            for c in data.ordered_chapters()
        ],
        "entities": [
            {
                "id": e.id, "type": e.type, "name": e.name, "role": e.role,
                "summary": e.summary, "isPov": e.is_pov, "aliases": e.aliases,
                "fields": e.cache,
            }
            for e in data.entities
        ],
        "beats": [
            {
                "key": b.key, "name": b.name, "pct": b.pct,
                "prompt": b.prompt, "answer": b.answer,
                "done": b.done, "sceneIds": b.scene_ids,
                "targetWord": b.target_word(data.targets.total_words),
            }
            for b in sorted(data.beats, key=lambda b: b.order)
        ],
        "events": [
            {
                "id": ev.id, "title": ev.title, "when": ev.story_date,
                "kind": ev.kind, "description": ev.description,
                "onPage": ev.on_page,
            }
            for ev in project.ordered_events()
        ],
        "notes": [
            {"id": n.id, "title": n.title, "kind": n.kind}
            for n in sorted(data.notes, key=lambda n: n.order)
        ],
    }


def _daily_series(data, days: int):
    from datetime import date, timedelta

    from . import stats

    totals = stats.daily_totals(data)
    today = date.today()
    return [
        totals.get((today - timedelta(days=offset)).isoformat(), (0, 0))[0]
        for offset in range(days - 1, -1, -1)
    ]


# -- scenes ----------------------------------------------------------------


@route("POST", "/api/scene/text")
def _scene_text(body: Dict[str, Any]) -> Any:
    with STATE.lock:
        project = STATE.require()
        scene_id = str(body.get("id") or "")
        if not project.data.scene(scene_id):
            raise ApiError("No such scene.", 404)
        return {"id": scene_id, "text": project.scene_text(scene_id)}


@route("PUT", "/api/scene/text")
def _scene_save(body: Dict[str, Any]) -> Any:
    with STATE.lock:
        project = STATE.require()
        scene_id = str(body.get("id") or "")
        if not project.data.scene(scene_id):
            raise ApiError("No such scene.", 404)
        words = project.save_scene_text(
            scene_id, str(body.get("text") or ""),
            snapshot=bool(body.get("snapshot", True)),
        )
        project.save()
        return {"id": scene_id, "words": words,
                "total": project.data.word_count}


@route("POST", "/api/scene/create")
def _scene_create(body: Dict[str, Any]) -> Any:
    with STATE.lock:
        project = STATE.require()
        chapter_id = str(body.get("chapterId") or "")
        if not project.data.chapter(chapter_id):
            raise ApiError("No such chapter.", 404)
        scene = project.add_scene(chapter_id, str(body.get("title") or ""))
        project.save()
        return {"id": scene.id, **_project_payload(project)}


@route("POST", "/api/scene/update")
def _scene_update(body: Dict[str, Any]) -> Any:
    with STATE.lock:
        project = STATE.require()
        scene = project.data.scene(str(body.get("id") or ""))
        if not scene:
            raise ApiError("No such scene.", 404)
        mapping = {
            "title": "title", "synopsis": "synopsis", "status": "status",
            "type": "scene_type", "povId": "pov_id", "goal": "goal",
            "conflict": "conflict", "disaster": "disaster",
            "reaction": "reaction", "dilemma": "dilemma",
            "decision": "decision", "valueStart": "value_start",
            "valueEnd": "value_end", "storyDate": "story_date",
            "notes": "notes", "include": "include_in_compile",
            "target": "target_words", "characterIds": "character_ids",
            "locationIds": "location_ids", "threadIds": "thread_ids",
        }
        for key, attr in mapping.items():
            if key in body:
                setattr(scene, attr, body[key])
        project.mark_dirty()
        project.save()
        return _project_payload(project)


@route("POST", "/api/chapter/create")
def _chapter_create(body: Dict[str, Any]) -> Any:
    with STATE.lock:
        project = STATE.require()
        chapter = project.add_chapter(str(body.get("title") or ""))
        project.save()
        return {"id": chapter.id, **_project_payload(project)}


@route("POST", "/api/entity/create")
def _entity_create(body: Dict[str, Any]) -> Any:
    with STATE.lock:
        project = STATE.require()
        entity = project.add_entity(
            str(body.get("type") or "character"),
            str(body.get("name") or "Unnamed"),
            role=str(body.get("role") or ""),
        )
        project.save()
        return {"id": entity.id, **_project_payload(project)}


# -- tools -----------------------------------------------------------------


@route("POST", "/api/analyse")
def _analyse(body: Dict[str, Any]) -> Any:
    from . import diagnostics

    with STATE.lock:
        project = STATE.require()
        scope = str(body.get("scope") or "scene")
        if scope == "scene":
            text = project.scene_text(str(body.get("id") or ""))
        elif scope == "chapter":
            from . import docxio

            chapter_id = str(body.get("id") or "")
            text = "\n\n".join(
                docxio.read_prose(project.abs(s.docx))
                for s in project.data.scenes_in(chapter_id) if s.docx
            )
        else:
            from . import docxio

            text = "\n\n".join(
                docxio.read_prose(project.abs(s.docx))
                for s in project.data.compile_scenes() if s.docx
            )

    report = diagnostics.analyse(text)
    return {
        "words": report.words,
        "sentences": report.sentences,
        "paragraphs": report.paragraphs,
        "metrics": report.metrics,
        "findings": [
            {
                "check": f.check, "severity": f.severity,
                "message": f.message, "examples": f.examples, "count": f.count,
            }
            for f in report.by_severity()
        ],
    }


@route("POST", "/api/compile")
def _compile(body: Dict[str, Any]) -> Any:
    from . import compiler

    with STATE.lock:
        project = STATE.require()
        options = compiler.CompileOptions(
            title_page=bool(body.get("titlePage", True)),
            running_header=bool(body.get("runningHeader", True)),
            table_of_contents=bool(body.get("toc", False)),
            include_synopses=bool(body.get("synopses", False)),
        )
        try:
            result = compiler.compile_manuscript(project, options)
        except OSError as exc:
            raise ApiError(str(exc), 500) from exc
        return {
            "path": str(result.path), "words": result.words,
            "chapters": result.chapters, "scenes": result.scenes,
            "skipped": result.skipped, "missing": result.missing,
            "summary": result.summary,
        }


@route("POST", "/api/backup")
def _backup(_body: Dict[str, Any]) -> Any:
    from . import backup

    with STATE.lock:
        project = STATE.require()
        path, message = backup.create_backup(project, reason="manual")
        return {"ok": path is not None, "path": str(path) if path else "",
                "message": message}


@route("POST", "/api/map/generate")
def _map_generate(body: Dict[str, Any]) -> Any:
    from . import mapgen, mapmaker

    with STATE.lock:
        project = STATE.require()
        params = mapgen.MapParams(
            seed_text=str(body.get("seed") or ""),
            name=str(body.get("name") or ""),
            shape=str(body.get("shape") or "continents"),
            climate=str(body.get("climate") or "temperate"),
            land_fraction=float(body.get("land") or 0.34),
        )
        gm = mapgen.generate(params)
        path = mapmaker.save_map(project.folder("maps"), gm)
        png = mapmaker.render_png(
            gm, project.folder("maps") / f"{gm.name}.png", scale=1.0,
        )
        return {"name": gm.name, "file": str(path), "png": str(png),
                "seed": gm.notes.splitlines()[2] if gm.notes else "",
                "shapes": len(gm.shapes), "pins": len(gm.pins)}


@route("POST", "/api/pick-folder")
def _pick_folder(body: Dict[str, Any]) -> Any:
    """
    Show a real Windows folder picker.

    A web page cannot open one, so the request comes here and Tk provides it.
    Tk must be driven from a fresh root each time or a second call after the
    first window is destroyed raises.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        raise ApiError("No folder picker is available on this system.", 501)

    initial = str(body.get("initial") or projects_root())
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        chosen = filedialog.askdirectory(
            parent=root,
            initialdir=initial,
            title=str(body.get("title") or "Choose a folder"),
        )
    finally:
        root.destroy()
    return {"path": chosen or ""}


@route("POST", "/api/reveal")
def _reveal(body: Dict[str, Any]) -> Any:
    target = str(body.get("path") or "")
    if not target:
        with STATE.lock:
            target = str(STATE.require().root)
    reveal_in_explorer(Path(target))
    return {"ok": True}


@route("POST", "/api/open-external")
def _open_external(body: Dict[str, Any]) -> Any:
    """Hand a document to Word. Local only - never a URL."""
    target = Path(str(body.get("path") or ""))
    if not target.exists():
        raise ApiError("That file no longer exists.", 404)
    return {"ok": open_in_default_app(target)}


# ==========================================================================
# HTTP plumbing
# ==========================================================================


class Handler(BaseHTTPRequestHandler):  # type: ignore[no-redef]
    server_version = f"NovelForge/{APP_VERSION}"
    protocol_version = "HTTP/1.1"

    # -- helpers -------------------------------------------------------
    def _send(self, status: int, body: bytes, content_type: str,
              extra: Optional[Dict[str, str]] = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # Nothing here should ever be cached by the embedded browser.
        self.send_header("Cache-Control", "no-store")
        # This app never loads anything remote; say so explicitly.
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
            "font-src 'self' data:; connect-src 'self'",
        )
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload: Any) -> None:
        self._send(status, json.dumps(payload, default=str).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _authorised(self) -> bool:
        return self.headers.get("X-NovelForge-Token") == STATE.token

    # -- verbs ---------------------------------------------------------
    def do_GET(self) -> None:
        path = unquote(urlparse(self.path).path)
        if path.startswith("/api/"):
            self._api("GET", path)
        else:
            self._static(path)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_POST(self) -> None:
        self._api("POST", unquote(urlparse(self.path).path))

    def do_PUT(self) -> None:
        self._api("PUT", unquote(urlparse(self.path).path))

    # -- api -----------------------------------------------------------
    def _api(self, method: str, path: str) -> None:
        handler = ROUTES.get((method, path))
        if handler is None:
            self._json(404, {"error": f"No route for {method} {path}"})
            return
        # /api/health is open so the launcher can poll before it has the token.
        if path != "/api/health" and not self._authorised():
            self._json(403, {"error": "Bad or missing token."})
            return

        body: Dict[str, Any] = {}
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._json(400, {"error": "Body was not valid JSON."})
                return
            if not isinstance(body, dict):
                self._json(400, {"error": "Body must be a JSON object."})
                return

        try:
            self._json(200, handler(body))
        except ApiError as exc:
            self._json(exc.status, {"error": str(exc)})
        except Exception as exc:
            # Never let one bad request kill the server the writer is using.
            self._json(500, {
                "error": f"{type(exc).__name__}: {exc}",
                "trace": traceback.format_exc()[-1200:],
            })

    # -- static --------------------------------------------------------
    def _static(self, path: str) -> None:
        if not WEB_ROOT.is_dir():
            self._send(
                503,
                b"<h1>Interface not built</h1><p>Run <code>npm run build</code> "
                b"in the <code>web</code> folder.</p>",
                "text/html; charset=utf-8",
            )
            return

        relative = path.lstrip("/") or "index.html"
        if relative.endswith("/"):
            relative += "index.html"
        target = (WEB_ROOT / relative).resolve()

        # Path traversal guard: resolve, then confirm it is still inside.
        try:
            target.relative_to(WEB_ROOT.resolve())
        except ValueError:
            self._json(403, {"error": "Forbidden"})
            return

        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            # Single-page app: unknown paths fall back to the shell.
            target = WEB_ROOT / "index.html"
        if not target.is_file():
            self._json(404, {"error": "Not found"})
            return

        content_type = mimetypes.guess_type(target.name)[0] \
            or "application/octet-stream"
        if content_type.startswith("text/") or content_type.endswith("json"):
            content_type += "; charset=utf-8"
        try:
            self._send(200, target.read_bytes(), content_type)
        except OSError as exc:
            self._json(500, {"error": str(exc)})

    # Quiet: a request log on every asset is noise in a desktop app.
    def log_message(self, fmt: str, *args: Any) -> None:
        return


def _free_port() -> int:
    """Ask the OS for an unused port so two copies never collide."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start() -> Tuple[ThreadingHTTPServer, str, str]:
    """
    Start the server on loopback. Returns (server, url, token).

    Bound explicitly to 127.0.0.1, never 0.0.0.0: the difference is whether
    other machines on the network can see it. They cannot.
    """
    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True,
                              name="novelforge-server")
    thread.start()
    return server, f"http://127.0.0.1:{port}", STATE.token
