"""
Crash-safe and OneDrive-safe file writing.

Your project folder sits inside OneDrive, which means two things can grab a
file while we are writing it: the sync client and (for .docx) Word itself.
Every write here goes to a temporary file in the same directory and is then
swapped into place with os.replace, which is atomic on NTFS. A half-written
manifest is therefore impossible - you either get the old file or the new one.

Windows will still occasionally refuse the swap with a sharing violation, so
the swap is retried with a short backoff before giving up.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Callable, Optional

# Windows sharing violations are transient; these bounds are generous enough
# to outlast an antivirus scan or a OneDrive upload without hanging the UI.
_RETRIES = 6
_BACKOFF_SECONDS = 0.12


class FileBusyError(OSError):
    """Raised when a file stayed locked by another process for too long."""


def _swap(tmp: Path, target: Path) -> None:
    """os.replace with retries for transient Windows locks."""
    last: Optional[BaseException] = None
    for attempt in range(_RETRIES):
        try:
            os.replace(tmp, target)
            return
        except PermissionError as exc:  # file locked by Word / OneDrive / AV
            last = exc
            time.sleep(_BACKOFF_SECONDS * (attempt + 1))
        except OSError as exc:
            last = exc
            break
    # The temp file holds the complete new content. Deleting it would throw
    # away the only copy on disk, so it is kept and named in the error - a
    # writer can rename it by hand and lose nothing.
    raise FileBusyError(
        f"Could not replace {target.name}: it is open in another program "
        f"(usually Word, sometimes OneDrive). Close it and try again.\n\n"
        f"Your new version is safe in '{tmp.name}' in the same folder."
    ) from last


def write_bytes_atomic(path: Path | str, data: bytes) -> Path:
    """Write bytes so the destination is never seen in a partial state."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp~")
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        # A partial temp file must not be left to be mistaken for a recovery
        # copy, nor to collide with the next write.
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    _swap(tmp, path)
    return path


def write_text_atomic(path: Path | str, text: str, encoding: str = "utf-8") -> Path:
    return write_bytes_atomic(path, text.encode(encoding))


def write_json_atomic(path: Path | str, payload: Any, indent: int = 2) -> Path:
    """Serialise first, then write - a serialisation error leaves the old file."""
    blob = json.dumps(payload, indent=indent, ensure_ascii=False, default=str)
    return write_text_atomic(path, blob)


def verify_written(path: Path, as_kind: Optional[str] = None) -> Optional[str]:
    """
    Check a just-written file before it is allowed to replace the real one.

    Returns None if it looks good, or a reason if it does not.

    A .docx is a zip. If the process is killed, the disk fills, or an
    antivirus scanner grabs the handle mid-write, what lands can be a
    truncated archive that Word refuses to open - and the atomic swap would
    then cheerfully install it over the good copy. Testing the central
    directory catches that in about a millisecond, which is a very cheap
    insurance premium on a novel.
    """
    try:
        size = path.stat().st_size
    except OSError as exc:
        return f"the new file could not be read back ({exc})"
    if size == 0:
        return "the new file came out empty"

    # `as_kind` matters: the file being checked is the temp copy, whose name
    # ends in ".tmp~". Judging by its own suffix would skip the zip check on
    # every document there is - which is exactly the case this exists for.
    suffix = (as_kind or path.suffix).lower()
    if suffix not in (".docx", ".zip", ".xlsx", ".pptx"):
        return None

    import zipfile

    try:
        with zipfile.ZipFile(path) as archive:
            broken = archive.testzip()
            if broken is not None:
                return f"the new file is damaged inside ({broken})"
            if not archive.namelist():
                return "the new file has no content"
    except zipfile.BadZipFile:
        return "the new file is not a valid Word document"
    except OSError as exc:
        return f"the new file could not be verified ({exc})"
    return None


def save_via_atomic(path: Path | str, saver: Callable[[Path], None],
                    verify: bool = True) -> Path:
    """
    Atomically produce a file using a callback that writes to a given path.

    Used for python-docx, whose Document.save() wants a path of its own.

    The temp file is verified before the swap, so a half-written document can
    never replace a good one. On failure the original is left untouched and
    the bad temp file is removed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp~")
    try:
        saver(tmp)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    if verify:
        problem = verify_written(tmp, as_kind=path.suffix)
        if problem:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise OSError(
                f"Could not save {path.name}: {problem}. "
                f"Your previous version has been left exactly as it was."
            )

    _swap(tmp, path)
    return path


def read_json(path: Path | str, default: Any = None) -> Any:
    """Read JSON, falling back to a sibling .bak if the primary is corrupt."""
    path = Path(path)
    for candidate in (path, path.with_suffix(path.suffix + ".bak")):
        if not candidate.exists():
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            continue
    return default


def keep_rolling_copy(path: Path | str) -> None:
    """
    Snapshot the current file to '<name>.bak' before it gets overwritten.

    Cheap insurance for the manifest: even if a write goes wrong in a way
    os.replace cannot protect against, the previous generation survives.
    """
    path = Path(path)
    if not path.exists():
        return
    try:
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    except OSError:
        pass


def is_locked(path: Path | str) -> bool:
    """True if the file exists but cannot currently be opened for writing."""
    path = Path(path)
    if not path.exists():
        return False
    try:
        with open(path, "ab"):
            return False
    except (PermissionError, OSError):
        return True


def onedrive_placeholder(path: Path | str) -> bool:
    """
    Detect a OneDrive 'online-only' placeholder file.

    Reading one triggers a blocking download. Files we created this session
    are always local, but a project restored onto a new machine may not be.
    """
    path = Path(path)
    try:
        attrs = os.stat(path).st_file_attributes  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return False
    FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x00040000
    FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x00400000
    FILE_ATTRIBUTE_OFFLINE = 0x00001000
    mask = (
        FILE_ATTRIBUTE_RECALL_ON_OPEN
        | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
        | FILE_ATTRIBUTE_OFFLINE
    )
    return bool(attrs & mask)


def unique_path(path: Path | str) -> Path:
    """
    Return `path`, or the first free ' (2)', ' (3)'... variant of it.

    Guards against silent overwrites, which are the worst failure a writing
    tool can have. Two characters both called "The Stranger" would otherwise
    share one sheet, and re-creating a scene whose file you chose to keep on
    disk would overwrite that file.
    """
    path = Path(path)
    if not path.exists():
        return path
    parent, stem, suffix = path.parent, path.stem, path.suffix
    for number in range(2, 500):
        candidate = parent / f"{stem} ({number}){suffix}"
        if not candidate.exists():
            return candidate
    # Never fall through to overwriting: take a certainly-unused name.
    import uuid

    return parent / f"{stem} ({uuid.uuid4().hex[:6]}){suffix}"


def safe_filename(name: str, fallback: str = "Untitled", maxlen: int = 96) -> str:
    """Turn an arbitrary title into something Windows will accept as a filename."""
    illegal = '<>:"/\\|?*'
    cleaned = "".join(" " if ch in illegal else ch for ch in (name or ""))
    cleaned = "".join(ch for ch in cleaned if ord(ch) >= 32)
    cleaned = " ".join(cleaned.split()).strip(" .")
    # Reserved DOS device names remain reserved even with an extension.
    reserved = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    if cleaned.upper() in reserved:
        cleaned = f"_{cleaned}"
    if not cleaned:
        cleaned = fallback
    return cleaned[:maxlen].strip()
