"""
Crash recovery, and remembering where you were.

Autosave already writes the editor into its Word document every thirty seconds,
so the worst case was losing half a minute of typing. That is not good enough:
half a minute is a paragraph, and the paragraph you lose is always the one that
was going well.

This module keeps a small journal beside the settings file, rewritten a couple
of seconds after you stop typing. It holds the text in the editor, where the
caret was, and which scene you were in. It costs a few milliseconds because it
is plain JSON - nothing here opens a Word document.

On the next start:

  * if the journal has text the .docx does not, the writer is offered it back;
  * otherwise it silently restores the project, scene, caret and scroll.

Deliberate design points:

  The journal lives with the settings, not inside the project. If the project
  folder is on a USB stick that was yanked - a fairly good way to crash an
  application - the recovery data is still on the machine.

  It records the document's modification time as well as its text. That is how
  "the file changed underneath us" is told apart from "we crashed": if the
  .docx was edited in Word since the journal was written, the journal is stale
  and offering it would overwrite newer work.

  Recovery is always *offered*, never applied. Silently replacing a document
  with a version the writer has not seen is the one failure worse than losing
  half a minute.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional

from .atomic import read_json, write_json_atomic
from .config import settings_file
from .model import now_iso

#: Bumped if the shape below changes incompatibly; an older file is ignored
#: rather than misread.
JOURNAL_VERSION = 1


def journal_path() -> Path:
    """Beside the settings file, so it follows the same override."""
    return settings_file().with_name("novelforge-session.json")


@dataclass
class Session:
    """Where the writer was, and what they had typed."""

    version: int = JOURNAL_VERSION
    project_root: str = ""
    scene_id: str = ""
    scene_docx: str = ""
    #: Editor contents at the moment the journal was written.
    text: str = ""
    #: True when `text` had not yet reached the document.
    dirty: bool = False
    #: Tk text index, e.g. "42.7".
    cursor: str = "1.0"
    #: Top of the visible area, 0.0 to 1.0.
    scroll: float = 0.0
    #: Modification time of the scene document when the journal was written.
    docx_mtime: float = 0.0
    #: Interface state worth restoring.
    distraction_free: bool = False
    focus_mode: bool = False
    binder_selection: str = ""
    written: str = field(default_factory=now_iso)
    clean_exit: bool = False

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Session":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


def save(session: Session) -> bool:
    """Write the journal. Never raises - a failure here must not stop typing."""
    try:
        session.written = now_iso()
        write_json_atomic(journal_path(), session.to_json())
        return True
    except Exception:
        return False


def load() -> Optional[Session]:
    data = read_json(journal_path(), None)
    if not isinstance(data, dict):
        return None
    try:
        session = Session.from_json(data)
    except Exception:
        return None
    if session.version != JOURNAL_VERSION:
        return None
    return session


def clear() -> None:
    try:
        journal_path().unlink(missing_ok=True)
    except OSError:
        pass


def mark_clean_exit() -> None:
    """
    Record that the application closed properly.

    The journal is kept rather than deleted, because it is also what restores
    the last scene and caret position on a normal start. Only the unsaved-text
    offer is suppressed.
    """
    session = load()
    if session is None:
        return
    session.clean_exit = True
    session.dirty = False
    session.text = ""
    save(session)


@dataclass
class Recovery:
    """An offer to restore work that never reached the document."""

    session: Session
    scene_title: str
    on_disk: str
    recovered: str

    @property
    def extra_words(self) -> int:
        return max(0, len(self.recovered.split()) - len(self.on_disk.split()))

    @property
    def summary(self) -> str:
        return (
            f"NovelForge did not close properly last time.\n\n"
            f"There is unsaved writing for '{self.scene_title}' from "
            f"{self.session.written.replace('T', ' at ')}.\n\n"
            f"On disk:    {len(self.on_disk.split()):,} words\n"
            f"Recovered:  {len(self.recovered.split()):,} words\n\n"
            f"Restore the recovered version?\n\n"
            f"The version currently on disk is kept as a copy either way."
        )


def pending(project) -> Optional[Recovery]:
    """
    Is there unsaved work to offer back for this project?

    Returns None whenever anything is uncertain. A false offer is worse than a
    missed one: it asks the writer to choose between two versions of their own
    prose with no way to tell which is which.
    """
    session = load()
    if session is None or session.clean_exit or not session.dirty:
        return None
    if not session.text.strip():
        return None
    try:
        if Path(session.project_root).resolve() != project.root.resolve():
            return None
    except OSError:
        return None

    scene = project.data.scene(session.scene_id)
    if scene is None or not scene.docx:
        return None

    path = project.abs(scene.docx)
    if not path.exists():
        return None

    # If the document changed after the journal was written, something else
    # (Word, a sync client, another copy of this program) has had it since.
    # The journal is stale and must not be offered.
    try:
        if path.stat().st_mtime > session.docx_mtime + 2.0:
            return None
    except OSError:
        return None

    from . import docxio

    try:
        on_disk = docxio.read_prose(path)
    except Exception:
        return None

    if on_disk.strip() == session.text.strip():
        return None         # nothing was actually lost

    return Recovery(session=session, scene_title=scene.title,
                    on_disk=on_disk, recovered=session.text)


def restore(project, recovery: Recovery) -> Path:
    """
    Put the recovered text into the scene, keeping the on-disk version.

    The displaced version is written next to the document rather than thrown
    away, because the writer is choosing between two things they cannot see
    side by side and may well choose wrong.
    """
    from . import docxio
    from .atomic import unique_path
    from .config import settings

    scene = project.data.scene(recovery.session.scene_id)
    if scene is None:
        raise ValueError("That scene is no longer in the project.")

    path = project.abs(scene.docx)
    if recovery.on_disk.strip():
        keep = unique_path(path.with_name(f"{path.stem} (before recovery).docx"))
        docxio.write_prose(
            keep, f"{scene.title} - version replaced by recovery",
            recovery.on_disk,
            font=settings["manuscript_font"],
            size=settings["manuscript_font_size"],
            line_spacing=settings["manuscript_line_spacing"],
            margin=settings["manuscript_margin"],
            first_line_indent=settings["manuscript_first_line_indent"],
        )

    project.save_scene_text(scene.id, recovery.recovered)
    return path
