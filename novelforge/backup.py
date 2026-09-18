"""
Backups and snapshots - the safety net.

Two independent mechanisms, because they fail differently:

  * **Snapshots** are per-document copies taken before each save. They answer
    "I rewrote this scene and the old version was better."
  * **Backups** are zipped copies of the entire project. They answer "the
    folder is gone" or "OneDrive did something inexplicable."

Both prune themselves. Both verify what they wrote before reporting success -
an unverified backup is just a feeling.
"""

from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from .atomic import safe_filename
from .config import FOLDERS, MANIFEST_NAME, settings

if TYPE_CHECKING:
    from .project import Project

# Folders excluded from a project backup: backing up the backups compounds.
SKIP_DIRS = {FOLDERS["backups"], FOLDERS["snapshots"]}
SKIP_SUFFIXES = {".tmp~"}
SKIP_PREFIXES = ("~$",)  # Word's lock files


def _stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H-%M-%S")


def _should_include(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    if relative.parts and relative.parts[0] in SKIP_DIRS:
        return False
    if path.suffix in SKIP_SUFFIXES:
        return False
    if path.name.startswith(SKIP_PREFIXES):
        return False
    return True


# ==========================================================================
# Snapshots
# ==========================================================================


def snapshot_document(project: "Project", path: Path, label: str = "") -> Optional[Path]:
    """
    Copy a document into _Snapshots before it is overwritten.

    Snapshots are grouped in a folder per document so the version history of
    one scene is easy to browse in Explorer.
    """
    path = Path(path)
    if not path.exists():
        return None
    try:
        from .atomic import unique_path

        group = path.stem
        folder = project.folder("snapshots") / safe_filename(group, "Document")
        folder.mkdir(parents=True, exist_ok=True)
        name = safe_filename(f"{_stamp()} {label or group}", "snapshot")
        # _stamp() has one-second resolution, and two saves inside one second
        # are entirely normal when autosave and an explicit Ctrl+S coincide.
        # Without unique_path the second would overwrite the first snapshot.
        target = unique_path(folder / f"{name}{path.suffix}")
        shutil.copy2(path, target)
        prune_snapshots(folder, settings["snapshot_retention_per_doc"])
        return target
    except OSError:
        # A failed snapshot must never block the save it was protecting.
        return None


def prune_snapshots(folder: Path, keep: int) -> int:
    """Delete the oldest snapshots beyond `keep`. Returns how many went."""
    if keep <= 0:
        return 0
    try:
        files = sorted(
            (p for p in folder.glob("*.docx") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return 0
    removed = 0
    for stale in files[keep:]:
        try:
            stale.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def list_snapshots(project: "Project", document_stem: str) -> List[Tuple[str, Path]]:
    """Available versions of one document, newest first, as (when, path)."""
    folder = project.folder("snapshots") / safe_filename(document_stem, "Document")
    if not folder.is_dir():
        return []
    out: List[Tuple[str, Path]] = []
    for path in folder.glob("*.docx"):
        try:
            when = datetime.fromtimestamp(path.stat().st_mtime)
            out.append((when.strftime("%d %b %Y  %H:%M:%S"), path))
        except OSError:
            continue
    return sorted(out, key=lambda item: item[1].stat().st_mtime, reverse=True)


def restore_snapshot(snapshot: Path, target: Path,
                     keep_current: bool = True) -> bool:
    """
    Put a snapshot back. The version being replaced is itself snapshotted
    first, so restoring is never destructive.
    """
    snapshot, target = Path(snapshot), Path(target)
    if not snapshot.exists():
        return False
    try:
        if keep_current and target.exists():
            sidecar = target.with_name(
                f"{target.stem} (replaced {_stamp()}){target.suffix}"
            )
            shutil.copy2(target, sidecar)
        shutil.copy2(snapshot, target)
        return True
    except OSError:
        return False


# ==========================================================================
# Full project backups
# ==========================================================================


def create_backup(project: "Project", reason: str = "manual") -> Tuple[Optional[Path], str]:
    """
    Zip the whole project into _Backups.

    Returns (path, message). The zip is reopened and tested before being
    reported as successful.
    """
    try:
        project.save()
    except OSError as exc:
        return None, f"Could not save the manifest first: {exc}"

    root = project.root
    backups = project.folder("backups")
    stem = safe_filename(project.data.title, "Project")
    target = backups / f"{stem} {_stamp()} ({reason}).zip"

    files: List[Path] = [
        p for p in root.rglob("*")
        if p.is_file() and _should_include(p, root)
    ]
    if not files:
        return None, "Nothing to back up."

    skipped = 0
    written = 0
    try:
        with zipfile.ZipFile(
            target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
        ) as archive:
            for path in files:
                try:
                    archive.write(path, path.relative_to(root))
                    written += 1
                except (OSError, ValueError):
                    # A file locked by Word is skipped, not fatal.
                    skipped += 1
    except OSError as exc:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        return None, f"Backup failed: {exc}"

    ok, verify_msg = verify_backup(target)
    if not ok:
        # A corrupt archive left in _Backups is worse than none: it looks like
        # a backup in the list and would fail only when relied on.
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        return None, (f"Backup failed verification and was discarded: "
                      f"{verify_msg}")

    pruned = prune_backups(project, settings["backup_retention"])
    size_mb = target.stat().st_size / (1024 * 1024)
    message = f"Backed up {written} files ({size_mb:.1f} MB)"
    if skipped:
        message += f", skipped {skipped} locked"
    if pruned:
        message += f", pruned {pruned} old"
    return target, message


def verify_backup(path: Path) -> Tuple[bool, str]:
    """
    Confirm a zip is readable and contains the manifest.

    zipfile.testzip() checks CRCs, which catches a truncated or corrupted
    archive - the exact failure a backup exists to survive.
    """
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return False, "the archive is empty"
    try:
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad is not None:
                return False, f"corrupt entry: {bad}"
            names = archive.namelist()
            if MANIFEST_NAME not in names:
                return False, f"{MANIFEST_NAME} is missing from the archive"
        return True, "verified"
    except (zipfile.BadZipFile, OSError) as exc:
        return False, str(exc)


def prune_backups(project: "Project", keep: int) -> int:
    if keep <= 0:
        return 0
    backups = project.folder("backups")
    try:
        archives = sorted(
            (p for p in backups.glob("*.zip") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        return 0
    removed = 0
    for stale in archives[keep:]:
        try:
            stale.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def list_backups(project: "Project") -> List[Tuple[str, str, Path]]:
    """Existing backups, newest first, as (when, size, path)."""
    backups = project.folder("backups")
    if not backups.is_dir():
        return []
    rows: List[Tuple[str, str, Path]] = []
    for path in backups.glob("*.zip"):
        try:
            stat = path.stat()
        except OSError:
            continue
        when = datetime.fromtimestamp(stat.st_mtime).strftime("%d %b %Y  %H:%M")
        size = f"{stat.st_size / (1024 * 1024):.1f} MB"
        rows.append((when, size, path))
    return sorted(rows, key=lambda r: r[2].stat().st_mtime, reverse=True)


def restore_backup(archive: Path, destination: Path) -> Tuple[bool, str]:
    """
    Extract a backup to a new folder.

    Deliberately never overwrites the live project - you get a copy and decide
    what to do with it. Restoring over working files is how people lose work.
    """
    archive, destination = Path(archive), Path(destination)
    ok, msg = verify_backup(archive)
    if not ok:
        return False, f"Refusing to restore: {msg}"
    if destination.exists() and any(destination.iterdir()):
        return False, f"'{destination.name}' already exists and is not empty."
    try:
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as zf:
            # Guard against path traversal in a hand-edited archive. A plain
            # string prefix check (`startswith`) is not enough here - a
            # sibling folder like "MyBook 2" starts with the same characters
            # as "MyBook" and would wrongly pass. Checking that the resolved
            # path is actually the destination or one of its descendants is
            # what the comment above always claimed this did.
            dest_root = destination.resolve()
            for name in zf.namelist():
                resolved = (destination / name).resolve()
                if resolved != dest_root and dest_root not in resolved.parents:
                    return False, f"Unsafe path in archive: {name}"
            zf.extractall(destination)
        return True, f"Restored to {destination}"
    except (zipfile.BadZipFile, OSError) as exc:
        return False, f"Restore failed: {exc}"


def backup_age_warning(project: "Project") -> str:
    """A nudge if the most recent backup is old. Empty string if fine."""
    backups = list_backups(project)
    if not backups:
        return "No backup exists yet for this project."
    try:
        newest = backups[0][2].stat().st_mtime
    except OSError:
        return ""
    days = (datetime.now() - datetime.fromtimestamp(newest)).days
    if days >= 7:
        return f"Your last backup was {days} days ago."
    return ""
