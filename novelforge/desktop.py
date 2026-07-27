"""
The desktop window.

Starts the local server, then opens a real application window pointed at it via
pywebview, which uses the WebView2 runtime already present on every Windows 10
and 11 machine (it ships with Edge). No browser, no address bar, no localhost
URL to type.

If pywebview or WebView2 is missing, this falls back to the default browser
rather than failing - a writer should never be blocked by a runtime detail.
"""

from __future__ import annotations

import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from typing import Optional

from . import APP_NAME, APP_VERSION
from .config import settings


def _wait_for_server(url: str, timeout: float = 15.0) -> bool:
    """Poll /api/health until the server answers. It starts in milliseconds."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=0.5) as r:
                if r.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.05)
    return False


def _inject_token(window, token: str) -> None:
    """
    Hand the session token to the page.

    The interface reads it from window.__NOVELFORGE__ and sends it back as a
    header on every request. It is generated fresh each launch and never
    written to disk.
    """
    try:
        window.evaluate_js(
            "window.__NOVELFORGE__ = "
            f"{{ token: {token!r}, version: {APP_VERSION!r}, desktop: true }};"
        )
    except Exception:
        pass


def run() -> int:
    from . import server

    srv, url, token = server.start()

    if not _wait_for_server(url):
        print("The local server did not start.", file=sys.stderr)
        return 1

    # Reopen whatever was last open, so launching lands you back at your desk.
    last = settings["last_project"]
    if last:
        try:
            request = urllib.request.Request(
                f"{url}/api/project/open",
                data=f'{{"path": {last!r}}}'.replace("'", '"').encode(),
                headers={"Content-Type": "application/json",
                         "X-NovelForge-Token": token},
                method="POST",
            )
            urllib.request.urlopen(request, timeout=10).read()
        except Exception:
            # A missing or moved folder must not stop the app opening.
            pass

    try:
        import webview
    except ImportError:
        print(
            "pywebview is not installed, so opening in your browser instead.\n"
            f"  {url}\n",
            file=sys.stderr,
        )
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return 0

    window = webview.create_window(
        APP_NAME,
        url,
        width=1560,
        height=980,
        min_size=(1024, 640),
        background_color="#0D1117",
        text_select=True,
        easy_drag=False,
    )

    def on_loaded() -> None:
        _inject_token(window, token)

    try:
        window.events.loaded += on_loaded
    except Exception:
        # Older pywebview: inject shortly after start instead.
        threading.Timer(1.2, lambda: _inject_token(window, token)).start()

    def on_closing() -> None:
        try:
            if server.STATE.project is not None:
                server.STATE.project.save(force=True)
                if settings["backup_on_close"]:
                    from . import backup

                    backup.create_backup(server.STATE.project, reason="close")
        except Exception:
            pass

    try:
        window.events.closing += on_closing
    except Exception:
        pass

    try:
        # gui=None lets pywebview pick the best available backend.
        webview.start(debug=False)
    except Exception as exc:
        print(f"Could not open a window ({exc}); using your browser.",
              file=sys.stderr)
        webbrowser.open(url)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    finally:
        on_closing()
        srv.shutdown()

    return 0
