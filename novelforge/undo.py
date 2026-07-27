"""
Undo and redo for everything that is not typing.

Tk's Text widget already gives the editor a proper undo stack. Everything
*around* the text had none: renaming a chapter, dragging a scene to a new
place, deleting a character, changing a field in the inspector. Those are the
edits a writer makes tentatively, and until now the only way back was a backup.

How it works
------------

Rather than writing an inverse operation for each of the thirty-odd things the
tool can do to a project - each one a chance to get the inverse subtly wrong -
this records a snapshot of the manifest before and after each action. Undo is
then "put the old manifest back", which cannot be subtly wrong.

The manifest is metadata only. On a 100-scene novel it is around 50 KB of JSON,
so a stack of forty snapshots is a couple of megabytes. `max_bytes` caps it for
the very large projects where that stops being true, dropping the oldest
entries first.

Prose is deliberately *not* snapshotted. It lives in the Word documents, where
the editor's own undo and the per-document version history already cover it,
and copying a 300,000 word manuscript on every rename would be absurd.

Deleted files
-------------

A snapshot restores the manifest, but a deleted document is still gone. So
deletions move files to a `_Trash` folder instead of unlinking them, and the
moves are recorded alongside the snapshot. Undo moves them back; redo moves
them out again. That also means "delete the files too" is no longer a
one-way door even without undo - the document is sitting in _Trash.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

#: (from, to) pairs describing files an action moved.
FileMoves = List[Tuple[str, str]]


@dataclass
class Entry:
    label: str
    before: Dict[str, Any]
    after: Dict[str, Any]
    moves: FileMoves = field(default_factory=list)
    #: Roughly how much memory this entry costs, cached to avoid re-measuring.
    size: int = 0


class UndoStack:
    """A bounded undo/redo history of manifest snapshots."""

    def __init__(self, limit: int = 40,
                 max_bytes: int = 24 * 1024 * 1024) -> None:
        self.limit = limit
        self.max_bytes = max_bytes
        self._done: List[Entry] = []
        self._undone: List[Entry] = []

    # -- state ----------------------------------------------------------
    @property
    def can_undo(self) -> bool:
        return bool(self._done)

    @property
    def can_redo(self) -> bool:
        return bool(self._undone)

    def undo_label(self) -> str:
        return self._done[-1].label if self._done else ""

    def redo_label(self) -> str:
        return self._undone[-1].label if self._undone else ""

    def clear(self) -> None:
        self._done.clear()
        self._undone.clear()

    def __len__(self) -> int:
        return len(self._done)

    # -- recording ------------------------------------------------------
    def push(self, label: str, before: Dict[str, Any], after: Dict[str, Any],
             moves: Optional[FileMoves] = None) -> bool:
        """
        Record a completed action. Returns False if nothing actually changed.

        Comparing the two snapshots means a dialog opened and cancelled, or an
        "Apply" that changed nothing, does not put a useless entry on the
        stack - the writer presses undo expecting their last *real* edit back.
        """
        if before == after and not moves:
            return False
        entry = Entry(label=label, before=before, after=after,
                      moves=list(moves or []))
        try:
            entry.size = len(json.dumps(before, default=str)) \
                + len(json.dumps(after, default=str))
        except (TypeError, ValueError):
            entry.size = 0
        self._done.append(entry)
        # A new action makes any redo history unreachable, which is what every
        # other program does and what people expect.
        self._undone.clear()
        self._trim()
        return True

    def _trim(self) -> None:
        while len(self._done) > self.limit:
            self._done.pop(0)
        total = sum(e.size for e in self._done)
        while total > self.max_bytes and len(self._done) > 1:
            total -= self._done.pop(0).size

    # -- replaying ------------------------------------------------------
    def undo(self) -> Optional[Entry]:
        if not self._done:
            return None
        entry = self._done.pop()
        self._undone.append(entry)
        return entry

    def redo(self) -> Optional[Entry]:
        if not self._undone:
            return None
        entry = self._undone.pop()
        self._done.append(entry)
        return entry


class Action:
    """
    Context manager wrapping one undoable change.

        with project.action("Delete scene"):
            project.delete_scene(scene_id, delete_files=True)

    Nesting is allowed and collapses into the outermost action, so a command
    that calls two project methods still reads as one step to the writer.

    If the body raises, the project is put back exactly as it was and nothing
    is recorded. A command that failed halfway through has left the manifest
    in a state nobody designed - two of five scenes deleted, a rename applied
    to one end of a link - and leaving that in place would make the next undo
    restore a half-edit.
    """

    def __init__(self, project, label: str) -> None:
        self.project = project
        self.label = label
        self.outermost = False

    def __enter__(self) -> "Action":
        project = self.project
        if getattr(project, "_action_depth", 0) == 0:
            project._undo_before = project.data.to_json()
            project._file_moves = []
            project._action_label = self.label
            self.outermost = True
        project._action_depth = getattr(project, "_action_depth", 0) + 1
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        project = self.project
        project._action_depth = max(0, getattr(project, "_action_depth", 1) - 1)
        if not self.outermost:
            return False
        if exc_type is not None:
            before = getattr(project, "_undo_before", None)
            moves = list(getattr(project, "_file_moves", []))
            project._undo_before = None
            project._file_moves = []
            if before is not None:
                try:
                    project.restore_snapshot(before, moves)
                except Exception:
                    # Nothing useful can be done if the rollback itself
                    # fails; let the original exception surface.
                    pass
            return False
        before = getattr(project, "_undo_before", None)
        if before is not None:
            project.history.push(
                getattr(project, "_action_label", self.label),
                before, project.data.to_json(),
                getattr(project, "_file_moves", []),
            )
        project._undo_before = None
        project._file_moves = []
        return False
