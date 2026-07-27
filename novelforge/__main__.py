"""
Entry point.

    python -m novelforge            the full application  (Tkinter)
    python -m novelforge --web      the new web interface (INCOMPLETE)
    python -m novelforge --serve    local server only, print the URL

The Tkinter interface is the default because it is the complete one: creating a
novel, writing, the map maker, the corkboard, the outline, the timeline, every
settings dialog, compiling and backups all work and are covered by tests.

The web interface is a redesign in progress. Its shell, settings screen and
editor are wired to the engine, but the maps, dashboard, library, character and
world screens do not exist yet, so it cannot replace this one. It is kept behind
--web so the work is not lost and can be finished later.
"""

from __future__ import annotations

import sys


def _missing() -> list[str]:
    missing: list[str] = []
    try:
        import docx  # noqa: F401
    except ImportError:
        missing.append("python-docx")
    try:
        import PIL  # noqa: F401
    except ImportError:
        missing.append("Pillow")
    return missing


def _complain(missing: list[str]) -> None:
    message = (
        f"{'These are' if len(missing) > 1 else 'This is'} needed and could "
        f"not be found:\n\n"
        + "\n".join(f"  - {name}" for name in missing)
        + "\n\nInstall with:\n\n"
        f"  {sys.executable} -m pip install " + " ".join(missing) + "\n"
    )
    print(message, file=sys.stderr)
    try:
        import tkinter
        from tkinter import messagebox

        root = tkinter.Tk()
        root.withdraw()
        messagebox.showerror("Missing dependency", message)
        root.destroy()
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])

    missing = _missing()
    if missing:
        _complain(missing)
        return 1

    if "--serve" in args:
        import time

        from . import server

        _srv, url, token = server.start()
        print(f"NovelForge is running at {url}")
        print(f"Session token: {token}")
        print("This address is on your own machine only. Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return 0

    if "--web" in args:
        from .desktop import run

        return run()

    # The default: the complete interface.
    from .ui.app import main as run_app

    return run_app()


if __name__ == "__main__":
    sys.exit(main())
