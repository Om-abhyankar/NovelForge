"""
Project lifecycle: create, open, save, and keep the manifest in step with disk.

Performance notes, because this runs on every keystroke's worth of state:

  * Opening a project reads exactly one file - project.json. No Word documents
    are parsed. Word counts come from the cached values in the manifest.
  * `sync_from_disk` only opens a document whose mtime differs from the cached
    value, so editing one scene in Word costs one file read, not two hundred.
  * Expensive sweeps (bracket tags, character mentions) are explicit commands,
    never background work.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from . import SCHEMA_VERSION
from .atomic import (
    keep_rolling_copy,
    read_json,
    safe_filename,
    unique_path,
    write_json_atomic,
)
from .config import FOLDERS, MANIFEST_NAME, projects_root, settings
from . import docxio, structures, templates
from .model import (
    ENTITY_LABELS,
    Beat,
    Chapter,
    Entity,
    Idea,
    Note,
    ProjectData,
    Scene,
    Targets,
    TimelineEvent,
    now_iso,
)
from .undo import Action, UndoStack

BRACKET_TAG = re.compile(r"\[([^\]\n]{2,120})\]")


class ProjectError(Exception):
    pass


# ==========================================================================
# Project
# ==========================================================================


class Project:
    """A project on disk plus its in-memory manifest."""

    def __init__(self, root: Path, data: ProjectData) -> None:
        self.root = Path(root)
        self.data = data
        self._dirty = False

        self.history = UndoStack()
        self._action_depth = 0
        self._action_label = ""
        self._undo_before: Optional[Dict[str, Any]] = None
        self._file_moves: List[Tuple[str, str]] = []

    # ------------------------------------------------------------------
    # Undo
    # ------------------------------------------------------------------

    def action(self, label: str) -> Action:
        """Wrap a structural change so it can be undone. See undo.Action."""
        return Action(self, label)

    def _trash(self, path: Path) -> Optional[Path]:
        """
        Move a document to _Trash instead of deleting it.

        Recorded so undo can put it back, and worth doing on its own account:
        "delete the files too" stops being a one-way door.
        """
        path = Path(path)
        if not path.exists():
            return None
        destination = unique_path(self.folder("trash") / path.name)
        try:
            shutil.move(str(path), str(destination))
        except OSError:
            return None
        self._file_moves.append((str(path), str(destination)))
        return destination

    def _apply_moves(self, moves: Sequence[Tuple[str, str]],
                     forward: bool) -> None:
        """Replay recorded file moves, or reverse them for an undo."""
        ordered = list(moves) if forward else list(reversed(moves))
        for origin, destination in ordered:
            source, target = (origin, destination) if forward \
                else (destination, origin)
            try:
                if not Path(source).exists():
                    continue
                Path(target).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(target))
            except OSError:
                # A file that cannot be moved back leaves the manifest
                # pointing at nothing, which Verify This Project reports.
                # Better than aborting the whole undo halfway through.
                continue

    def restore_snapshot(self, manifest: Dict[str, Any],
                         moves: Sequence[Tuple[str, str]] = ()) -> None:
        """Put the manifest back and reverse any file moves it came with."""
        self.data = ProjectData.from_json(manifest)
        self._apply_moves(moves, forward=False)
        self.mark_dirty()

    def undo(self) -> Optional[str]:
        """Step back one structural change. Returns its label, or None."""
        entry = self.history.undo()
        if entry is None:
            return None
        self.data = ProjectData.from_json(entry.before)
        self._apply_moves(entry.moves, forward=False)
        self.mark_dirty()
        return entry.label

    def redo(self) -> Optional[str]:
        entry = self.history.redo()
        if entry is None:
            return None
        self.data = ProjectData.from_json(entry.after)
        self._apply_moves(entry.moves, forward=True)
        self.mark_dirty()
        return entry.label

    # -- paths ----------------------------------------------------------
    def folder(self, key: str) -> Path:
        path = self.root / FOLDERS[key]
        path.mkdir(parents=True, exist_ok=True)
        return path

    def abs(self, relative: str) -> Path:
        return self.root / relative

    def rel(self, path: Path) -> str:
        try:
            return str(Path(path).relative_to(self.root))
        except ValueError:
            return str(path)

    @property
    def manifest_path(self) -> Path:
        return self.root / MANIFEST_NAME

    @property
    def compiled_path(self) -> Path:
        stem = safe_filename(self.data.title, "Manuscript")
        return self.folder("compiled") / f"{stem} - Manuscript.docx"

    # -- persistence ----------------------------------------------------
    def mark_dirty(self) -> None:
        self._dirty = True

    @property
    def dirty(self) -> bool:
        return self._dirty

    def save(self, force: bool = False) -> None:
        if not (self._dirty or force):
            return
        self.sync_beat_archive()
        self.data.schema_version = SCHEMA_VERSION
        self.data.touch()
        keep_rolling_copy(self.manifest_path)
        write_json_atomic(self.manifest_path, self.data.to_json())
        self._dirty = False

    # ------------------------------------------------------------------
    # Opening and creating
    # ------------------------------------------------------------------

    @classmethod
    def open(cls, root: Path | str) -> "Project":
        root = Path(root)
        manifest = root / MANIFEST_NAME
        if not manifest.exists():
            raise ProjectError(f"No {MANIFEST_NAME} in {root}")
        raw = read_json(manifest)
        if not isinstance(raw, dict):
            raise ProjectError(
                f"{MANIFEST_NAME} is unreadable and no usable .bak was found."
            )
        data = ProjectData.from_json(raw)
        project = cls(root, data)
        data.opened = now_iso()
        project.mark_dirty()
        return project

    @classmethod
    def create(
        cls,
        title: str,
        author: str = "",
        genre: str = "",
        structure: str = "three_act",
        target_words: int = 90000,
        daily_words: int = 1000,
        deadline: str = "",
        parent: Optional[Path] = None,
        packs: Optional[Sequence[str]] = None,
        progress: Optional[Callable[[str], None]] = None,
    ) -> "Project":
        """
        Scaffold a whole project: folders, manifest, and every starter document.

        `packs` selects optional extras - "fantasy", "mystery", "romance".
        """
        say = progress or (lambda _msg: None)

        parent = Path(parent) if parent else projects_root()
        folder_name = safe_filename(title, "Untitled Novel")
        root = parent / folder_name
        if root.exists() and any(root.iterdir()):
            raise ProjectError(f"'{root}' already exists and is not empty.")
        root.mkdir(parents=True, exist_ok=True)

        surname = author.strip().split()[-1] if author.strip() else ""
        data = ProjectData(
            title=title,
            author=author,
            author_surname=surname,
            genre=genre,
            structure=structure,
            targets=Targets(
                total_words=target_words,
                daily_words=daily_words,
                deadline=deadline,
            ),
        )
        project = cls(root, data)

        say("Creating folders...")
        for key in FOLDERS:
            project.folder(key)

        say("Loading story structure...")
        project.apply_structure(structure, write_doc=False)

        say("Writing planning documents...")
        project.generate_planning_docs()

        say("Writing world bible...")
        project.generate_world_bible(packs or [])

        say("Writing publishing documents...")
        project.generate_publishing_docs()

        say("Writing reference documents...")
        project.generate_reference_docs(packs or [])

        say("Creating first chapter...")
        chapter = project.add_chapter("Chapter One")
        project.add_scene(chapter.id, "Opening Scene")

        say("Writing outline...")
        project.write_outline_doc()

        say("Saving...")
        project.save(force=True)
        say("Done.")
        return project

    # ------------------------------------------------------------------
    # Structure / beats
    # ------------------------------------------------------------------

    def apply_structure(self, key: str, write_doc: bool = True) -> None:
        """
        Switch the project to a structural framework.

        Frameworks do not share beat keys - Three-Act has "hook", Save the Cat
        has "opening_image" - so switching cannot simply carry beats across.
        Instead every framework's answers are archived under its own name and
        restored when you return to it. Try all nine; lose nothing.
        """
        self._archive_beats()
        framework = structures.framework(key)
        self.data.structure = framework.key
        self.data.beats = []
        for i, beat in enumerate(framework.beats):
            stored = self.data.beat_archive.get(f"{framework.key}:{beat.key}", {})
            self.data.beats.append(
                Beat(
                    key=beat.key,
                    name=beat.name,
                    pct=beat.pct,
                    prompt=beat.prompt,
                    answer=stored.get("answer", ""),
                    scene_ids=list(stored.get("scene_ids") or []),
                    done=bool(stored.get("done", False)),
                    order=i,
                )
            )
        self.mark_dirty()
        if write_doc:
            self.write_outline_doc()

    def _archive_beats(self) -> None:
        """Stash the current framework's answers before they are replaced."""
        if not self.data.structure:
            return
        for beat in self.data.beats:
            if beat.answer or beat.scene_ids or beat.done:
                self.data.beat_archive[f"{self.data.structure}:{beat.key}"] = {
                    "answer": beat.answer,
                    "scene_ids": list(beat.scene_ids),
                    "done": beat.done,
                }

    def sync_beat_archive(self) -> None:
        """
        Mirror live beats into the archive.

        Called before saving so an answer typed and then never followed by a
        framework switch is still safe.
        """
        self._archive_beats()

    # ------------------------------------------------------------------
    # Chapters
    # ------------------------------------------------------------------

    def add_chapter(self, title: str = "", part: str = "") -> Chapter:
        order = self.data.next_order(self.data.chapters)
        title = title or f"Chapter {order + 1}"
        chapter = Chapter(title=title, order=order, part=part)
        # unique_path so a new chapter never adopts the leftover folder of a
        # deleted one whose files the user chose to keep.
        folder = unique_path(self.folder("manuscript") / safe_filename(
            f"{order + 1:02d} {title}", f"{order + 1:02d} Chapter"
        ))
        folder.mkdir(parents=True, exist_ok=True)
        chapter.folder = self.rel(folder)
        self.data.chapters.append(chapter)
        self.mark_dirty()
        return chapter

    def rename_chapter(self, chapter_id: str, title: str) -> None:
        chapter = self.data.chapter(chapter_id)
        if not chapter or not title.strip():
            return
        chapter.title = title.strip()
        chapter.modified = now_iso()
        self.mark_dirty()

    def delete_chapter(self, chapter_id: str, delete_files: bool = False) -> None:
        chapter = self.data.chapter(chapter_id)
        if not chapter:
            return
        for scene in list(self.data.scenes_in(chapter_id)):
            self.delete_scene(scene.id, delete_files=delete_files)
        self.data.chapters = [c for c in self.data.chapters if c.id != chapter_id]
        if delete_files and chapter.folder:
            target = self.abs(chapter.folder)
            if target.is_dir():
                # Moved rather than rmtree'd: the scenes inside have already
                # gone to _Trash individually, but anything the writer put in
                # the folder by hand would otherwise be destroyed outright,
                # and there would be nothing for undo to restore.
                self._trash(target)
        self._renumber(self.data.chapters)
        self.mark_dirty()

    # ------------------------------------------------------------------
    # Scenes
    # ------------------------------------------------------------------

    def add_scene(self, chapter_id: str, title: str = "",
                  synopsis: str = "", body: str = "") -> Scene:
        chapter = self.data.chapter(chapter_id)
        if not chapter:
            raise ProjectError("Unknown chapter")
        siblings = self.data.scenes_in(chapter_id)
        order = self.data.next_order(siblings)
        title = title or f"Scene {order + 1}"

        scene = Scene(
            title=title, chapter_id=chapter_id, order=order, synopsis=synopsis
        )
        folder = self.abs(chapter.folder) if chapter.folder else self.folder("manuscript")
        folder.mkdir(parents=True, exist_ok=True)
        chapter_index = chapter.order + 1
        filename = safe_filename(
            f"{chapter_index:02d}-{order + 1:02d} {title}", "Scene"
        )
        # Ordering alone does not guarantee a free name: deleting a scene while
        # keeping its file, then adding another, can compute the same filename
        # and would silently overwrite the kept prose.
        path = unique_path(folder / f"{filename}.docx")
        docxio.write_prose(
            path, title, body,
            font=settings["manuscript_font"],
            size=settings["manuscript_font_size"],
            line_spacing=settings["manuscript_line_spacing"],
            margin=settings["manuscript_margin"],
            first_line_indent=settings["manuscript_first_line_indent"],
            synopsis=synopsis,
        )
        scene.docx = self.rel(path)
        scene.docx_mtime = docxio.docx_mtime(path)
        scene.word_count = docxio.word_count(body)
        self.data.scenes.append(scene)
        self.mark_dirty()
        return scene

    def scene_text(self, scene_id: str) -> str:
        scene = self.data.scene(scene_id)
        if not scene or not scene.docx:
            return ""
        return docxio.read_prose(self.abs(scene.docx))

    def save_scene_text(self, scene_id: str, body: str,
                        snapshot: bool = True) -> int:
        """
        Write prose back to the scene document. Returns the new word count.

        The word count is computed from the text in hand rather than by
        re-reading the file, which keeps saving cheap.
        """
        scene = self.data.scene(scene_id)
        if not scene:
            return 0
        path = self.abs(scene.docx) if scene.docx else None
        if path is None:
            chapter = self.data.chapter(scene.chapter_id)
            folder = self.abs(chapter.folder) if chapter and chapter.folder \
                else self.folder("manuscript")
            path = folder / f"{safe_filename(scene.title, 'Scene')}.docx"
            scene.docx = self.rel(path)

        if snapshot and settings["snapshot_on_save"] and path.exists():
            from .backup import snapshot_document

            snapshot_document(self, path, scene.title)

        docxio.write_prose(
            path, scene.title, body,
            font=settings["manuscript_font"],
            size=settings["manuscript_font_size"],
            line_spacing=settings["manuscript_line_spacing"],
            margin=settings["manuscript_margin"],
            first_line_indent=settings["manuscript_first_line_indent"],
            synopsis=scene.synopsis,
        )
        scene.word_count = docxio.word_count(body)
        scene.docx_mtime = docxio.docx_mtime(path)
        scene.modified = now_iso()
        self.mark_dirty()
        return scene.word_count

    def rename_scene(self, scene_id: str, title: str) -> None:
        scene = self.data.scene(scene_id)
        if not scene or not title.strip():
            return
        scene.title = title.strip()
        scene.modified = now_iso()
        self.mark_dirty()

    def delete_scene(self, scene_id: str, delete_files: bool = False) -> None:
        scene = self.data.scene(scene_id)
        if not scene:
            return
        chapter_id = scene.chapter_id
        self.data.scenes = [s for s in self.data.scenes if s.id != scene_id]
        for beat in self.data.beats:
            if scene_id in beat.scene_ids:
                beat.scene_ids.remove(scene_id)
        # Archived beats from other frameworks hold scene ids too; a deleted
        # scene must not resurface as a dangling link when you switch back.
        for stored in self.data.beat_archive.values():
            ids = stored.get("scene_ids")
            if isinstance(ids, list) and scene_id in ids:
                ids.remove(scene_id)
        for event in self.data.events:
            if event.scene_id == scene_id:
                event.scene_id = ""
        if delete_files and scene.docx:
            self._trash(self.abs(scene.docx))
        self._renumber(self.data.scenes_in(chapter_id))
        self.mark_dirty()

    def move_scene(self, scene_id: str, delta: int) -> None:
        """Nudge a scene up or down inside its chapter."""
        scene = self.data.scene(scene_id)
        if not scene:
            return
        siblings = self.data.scenes_in(scene.chapter_id)
        index = next((i for i, s in enumerate(siblings) if s.id == scene_id), -1)
        target = index + delta
        if index < 0 or not (0 <= target < len(siblings)):
            return
        siblings[index], siblings[target] = siblings[target], siblings[index]
        self._renumber(siblings)
        self.mark_dirty()

    def move_chapter(self, chapter_id: str, delta: int) -> None:
        chapters = self.data.ordered_chapters()
        index = next((i for i, c in enumerate(chapters) if c.id == chapter_id), -1)
        target = index + delta
        if index < 0 or not (0 <= target < len(chapters)):
            return
        chapters[index], chapters[target] = chapters[target], chapters[index]
        self._renumber(chapters)
        self.mark_dirty()

    def reassign_scene(self, scene_id: str, chapter_id: str) -> None:
        """
        Move a scene into another chapter, taking its document with it.

        The file must move too. Leaving it in the old chapter's folder means
        deleting that chapter with 'delete files' would destroy prose that now
        belongs to a different chapter.
        """
        scene = self.data.scene(scene_id)
        target = self.data.chapter(chapter_id)
        if not scene or not target or scene.chapter_id == chapter_id:
            return
        old_chapter = scene.chapter_id
        # Order must be computed before the reparent, or scenes_in already
        # counts this scene and the new order collides with an existing one.
        new_order = self.data.next_order(self.data.scenes_in(chapter_id))
        scene.chapter_id = chapter_id
        scene.order = new_order

        if scene.docx and target.folder:
            source = self.abs(scene.docx)
            destination = self.abs(target.folder)
            if source.exists() and destination.is_dir() \
                    and source.parent.resolve() != destination.resolve():
                moved = unique_path(destination / source.name)
                try:
                    shutil.move(str(source), str(moved))
                    scene.docx = self.rel(moved)
                    scene.docx_mtime = docxio.docx_mtime(moved)
                except (OSError, shutil.Error):
                    # Locked by Word: keep pointing at where it actually is.
                    pass

        self._renumber(self.data.scenes_in(old_chapter))
        scene.modified = now_iso()
        self.mark_dirty()

    @staticmethod
    def _renumber(items: Sequence) -> None:
        for i, item in enumerate(items):
            item.order = i

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    _ENTITY_FOLDER = {
        "character": "characters",
        "location": "locations",
        "item": "items",
        "faction": "factions",
        "thread": "threads",
    }

    _ENTITY_PREFIX = {
        "character": "Character",
        "location": "Location",
        "item": "Item",
        "faction": "Faction",
        "thread": "Thread",
    }

    def add_entity(self, entity_type: str, name: str,
                   role: str = "", summary: str = "") -> Entity:
        if entity_type not in self._ENTITY_FOLDER:
            raise ProjectError(f"Unknown entity type: {entity_type}")
        order = self.data.next_order(self.data.entities_of(entity_type))
        entity = Entity(
            type=entity_type, name=name, role=role,
            summary=summary, order=order,
        )
        folder = self.folder(self._ENTITY_FOLDER[entity_type])
        prefix = self._ENTITY_PREFIX[entity_type]
        # Two characters may legitimately share a name ("The Stranger"); without
        # unique_path the second would silently take over the first one's sheet.
        path = unique_path(
            folder / f"{safe_filename(f'{prefix} - {name}', prefix)}.docx"
        )

        sections = templates.sections_for(entity_type)
        seed: Dict[str, str] = {}
        if entity_type == "character" and role:
            seed["Narrative role"] = role
        if name:
            first_field = sections[0][1][0][0] if sections and sections[0][1] else ""
            if first_field in ("Name", "Thread name"):
                seed[first_field] = name

        docxio.write_field_sheet(
            path,
            name,
            sections,
            subtitle=role or summary,
            kicker=templates.kicker_for(entity_type),
            values=seed,
        )
        entity.docx = self.rel(path)
        entity.cache_mtime = docxio.docx_mtime(path)
        entity.cache = seed
        self.data.entities.append(entity)
        self.mark_dirty()
        return entity

    def rename_entity(self, entity_id: str, name: str) -> None:
        entity = self.data.entity(entity_id)
        if not entity or not name.strip():
            return
        entity.name = name.strip()
        entity.modified = now_iso()
        self.mark_dirty()

    def delete_entity(self, entity_id: str, delete_files: bool = False) -> None:
        entity = self.data.entity(entity_id)
        if not entity:
            return
        self.data.entities = [e for e in self.data.entities if e.id != entity_id]
        # Unlink from every scene that referenced it.
        for scene in self.data.scenes:
            for attr in ("character_ids", "location_ids", "item_ids",
                         "faction_ids", "thread_ids"):
                ids = getattr(scene, attr)
                if entity_id in ids:
                    ids.remove(entity_id)
            if scene.pov_id == entity_id:
                scene.pov_id = ""
        for event in self.data.events:
            if entity_id in event.character_ids:
                event.character_ids.remove(entity_id)
            if event.location_id == entity_id:
                event.location_id = ""
        if delete_files and entity.docx:
            try:
                self._trash(self.abs(entity.docx))
            except OSError:
                pass
        self._renumber(self.data.entities_of(entity.type))
        self.mark_dirty()

    def entity_fields(self, entity_id: str, refresh: bool = True) -> Dict[str, str]:
        """
        Read an entity's sheet, using the cache unless the file changed.

        This is the sync point between Word and the tool: edit a character
        sheet in Word, and the next read picks it up because the mtime moved.
        """
        entity = self.data.entity(entity_id)
        if not entity or not entity.docx:
            return {}
        path = self.abs(entity.docx)
        mtime = docxio.docx_mtime(path)
        if refresh and mtime and mtime != entity.cache_mtime:
            entity.cache = docxio.read_field_sheet(path)
            entity.cache_mtime = mtime
            self._promote_entity_fields(entity)
            self.mark_dirty()
        return entity.cache

    def _promote_entity_fields(self, entity: Entity) -> None:
        """Copy a few sheet answers up into the manifest for fast display."""
        fields = entity.cache
        if entity.type == "character":
            entity.role = fields.get("Narrative role", entity.role) or entity.role
            pov = (fields.get("Is this a POV character?") or "").strip().lower()
            if pov:
                entity.is_pov = pov.startswith("y")
            aliases = fields.get("Aliases & nicknames", "")
            if aliases:
                entity.aliases = [
                    a.strip() for a in re.split(r"[,;\n]", aliases) if a.strip()
                ]
            summary = fields.get("What the story does to them", "")
            if summary:
                entity.summary = summary.splitlines()[0][:140]
        elif entity.type == "location":
            entity.role = fields.get("Type", entity.role) or entity.role
            atmosphere = fields.get("Overall atmosphere", "")
            if atmosphere:
                entity.summary = atmosphere.splitlines()[0][:140]
        elif entity.type == "thread":
            entity.role = fields.get("Type", entity.role) or entity.role
            question = fields.get("The question this thread asks", "")
            if question:
                entity.summary = question.splitlines()[0][:140]
        elif entity.type in ("item", "faction"):
            entity.role = fields.get("Type", entity.role) or entity.role

    def rewrite_entity_sheet(self, entity_id: str) -> Optional[Path]:
        """
        Regenerate a sheet from the template, preserving typed answers.

        Used after a template gains new fields - you get the new rows without
        losing what you already wrote.
        """
        entity = self.data.entity(entity_id)
        if not entity or not entity.docx:
            return None
        path = self.abs(entity.docx)
        existing = docxio.read_field_sheet(path) if path.exists() else {}
        # read_field_sheet returns {} for a document python-docx cannot parse,
        # which is indistinguishable from a genuinely blank sheet. Rewriting
        # from {} would erase everything the writer typed, so refuse instead.
        if path.exists() and not existing and not docxio.prose_readable(path):
            raise ProjectError(
                f"'{path.name}' could not be read, so it has not been touched. "
                f"It may be open in Word, still downloading from OneDrive, or "
                f"damaged - in which case restore it from a backup."
            )
        docxio.write_field_sheet(
            path,
            entity.name,
            templates.sections_for(entity.type),
            subtitle=entity.role or entity.summary,
            kicker=templates.kicker_for(entity.type),
            values=existing,
        )
        entity.cache = existing
        entity.cache_mtime = docxio.docx_mtime(path)
        self.mark_dirty()
        return path

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    def add_note(self, title: str, kind: str = "note", body: str = "") -> Note:
        order = self.data.next_order(self.data.notes)
        note = Note(title=title, kind=kind, order=order)
        folder = self.folder("research" if kind == "research" else "notes")
        path = unique_path(folder / f"{safe_filename(title, 'Note')}.docx")
        docxio.write_prose(
            path, title, body,
            font=settings["manuscript_font"],
            size=11, line_spacing=1.15, margin=0.9, first_line_indent=0.0,
        )
        note.docx = self.rel(path)
        self.data.notes.append(note)
        self.mark_dirty()
        return note

    def delete_note(self, note_id: str, delete_files: bool = False) -> None:
        note = self.data.note(note_id)
        if not note:
            return
        self.data.notes = [n for n in self.data.notes if n.id != note_id]
        if delete_files and note.docx:
            try:
                self._trash(self.abs(note.docx))
            except OSError:
                pass
        self.mark_dirty()

    def set_note_links(self, note_id: str, target_ids: Sequence[str]) -> None:
        """
        Attach a note to the scenes and characters it is research *for*.

        Ids that no longer exist are dropped rather than stored, so a deleted
        character cannot leave a note pointing at nothing.
        """
        note = self.data.note(note_id)
        if not note:
            return
        valid = {e.id for e in self.data.entities}
        valid |= {s.id for s in self.data.scenes}
        valid |= {c.id for c in self.data.chapters}
        note.links = [t for t in dict.fromkeys(target_ids) if t in valid]
        note.modified = now_iso()
        self.mark_dirty()

    def notes_for(self, target_id: str) -> List[Note]:
        """Every note attached to a scene, character or chapter."""
        return [n for n in self.data.notes if target_id in (n.links or [])]

    # ------------------------------------------------------------------
    # Idea inbox
    # ------------------------------------------------------------------

    def add_idea(self, text: str, tags: Sequence[str] = ()) -> Idea:
        idea = Idea(text=text.strip(), tags=list(tags))
        self.data.ideas.append(idea)
        self.mark_dirty()
        return idea

    def set_idea_status(self, idea_id: str, status: str,
                        target_id: str = "") -> None:
        idea = self.data.idea(idea_id)
        if not idea:
            return
        idea.status = status
        idea.target_id = target_id
        self.mark_dirty()

    def delete_idea(self, idea_id: str) -> None:
        self.data.ideas = [i for i in self.data.ideas if i.id != idea_id]
        self.mark_dirty()

    def suggest_placements(self, idea_id: str,
                           limit: int = 6) -> List[Tuple[str, str, float]]:
        """
        Where an idea might belong, worked out by word overlap.

        Deliberately not clever. It scores the idea's distinctive words against
        every scene title, synopsis and entity name, and returns the best few.
        A writer only needs a shortlist to jump from - and a plain, explainable
        score is easier to trust than a black box that is right slightly more
        often. Returns (id, label, score), best first.
        """
        idea = self.data.idea(idea_id)
        if not idea:
            return []
        stop = {"the", "a", "an", "and", "or", "but", "if", "of", "to", "in",
                "on", "for", "with", "at", "by", "from", "is", "was", "be",
                "that", "this", "it", "he", "she", "they", "what", "when",
                "who", "her", "his", "them", "their", "should", "could",
                "would", "maybe", "about", "into", "then", "than", "have"}
        terms = {w for w in re.findall(r"[a-z']{3,}", idea.text.lower())
                 if w not in stop}
        if not terms:
            return []

        scored: List[Tuple[str, str, float]] = []

        def score_against(text: str) -> float:
            words = set(re.findall(r"[a-z']{3,}", (text or "").lower()))
            if not words:
                return 0.0
            hits = terms & words
            if not hits:
                return 0.0
            # Normalised by the idea's own length so a long idea does not
            # automatically beat a short one.
            return len(hits) / len(terms)

        for scene in self.data.ordered_scenes():
            haystack = " ".join([scene.title, scene.synopsis, scene.notes,
                                 scene.goal, scene.conflict, scene.disaster])
            value = score_against(haystack)
            if value > 0:
                scored.append((scene.id, f"Scene - {scene.display}", value))

        for entity in self.data.entities:
            haystack = " ".join([entity.name, entity.summary, entity.role]
                                + list(entity.cache.values()))
            value = score_against(haystack)
            if value > 0:
                scored.append((
                    entity.id,
                    f"{ENTITY_LABELS.get(entity.type, entity.type)} - "
                    f"{entity.display}",
                    value,
                ))

        for chapter in self.data.ordered_chapters():
            value = score_against(f"{chapter.title} {chapter.synopsis}")
            if value > 0:
                scored.append((chapter.id, f"Chapter - {chapter.display}", value))

        scored.sort(key=lambda row: -row[2])
        return scored[:limit]

    # ------------------------------------------------------------------
    # Branching drafts
    # ------------------------------------------------------------------
    #
    # A branch is a stored copy of a scene's prose. `scene.docx` is always the
    # live file, so compiling, word counts, search and every export keep working
    # without knowing branches exist. Switching writes the live file out to the
    # branch being left and copies the branch being entered in.

    def _draft_folder(self, scene: Scene) -> Path:
        folder = (self.folder("drafts")
                  / safe_filename(scene.title or scene.id, "Scene"))
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def _draft_path(self, scene: Scene, name: str) -> Path:
        return self._draft_folder(scene) / f"{safe_filename(name, 'Draft')}.docx"

    def list_drafts(self, scene_id: str) -> List[str]:
        """
        Every branch of a scene, "Main" always first.

        Main is implicit rather than stored, so it has to be re-added here or a
        scene that branched once would lose the way back to its original.
        """
        scene = self.data.scene(scene_id)
        if not scene:
            return []
        return list(dict.fromkeys(
            ["Main"] + list(scene.drafts) + [scene.active_draft or "Main"]
        ))

    def create_draft(self, scene_id: str, name: str,
                     copy_current: bool = True) -> str:
        """
        Start a new branch of a scene.

        `copy_current=True` branches from what is there now, which is what
        "try something different with this chapter" means. False starts empty,
        for a genuine rewrite from nothing.
        """
        scene = self.data.scene(scene_id)
        if not scene:
            raise ProjectError("That scene is no longer in the project.")
        name = (name or "").strip() or "Untitled draft"
        if name in self.list_drafts(scene_id):
            raise ProjectError(f"'{name}' already exists for this scene.")

        # Park the live text under the branch we are on before leaving it.
        self._store_draft(scene, scene.active_draft or "Main")

        body = self.scene_text(scene_id) if copy_current else ""
        docxio.write_prose(
            self.abs(scene.docx), scene.title, body,
            font=settings["manuscript_font"],
            size=settings["manuscript_font_size"],
            line_spacing=settings["manuscript_line_spacing"],
            margin=settings["manuscript_margin"],
            first_line_indent=settings["manuscript_first_line_indent"],
        )
        scene.drafts = list(dict.fromkeys(list(scene.drafts) + [name]))
        scene.active_draft = name
        self._store_draft(scene, name)
        scene.word_count = docxio.word_count(body)
        scene.docx_mtime = docxio.docx_mtime(self.abs(scene.docx))
        scene.modified = now_iso()
        self.mark_dirty()
        return name

    def _store_draft(self, scene: Scene, name: str) -> None:
        """Copy the live file into the named branch slot."""
        source = self.abs(scene.docx)
        if not source.exists():
            return
        try:
            shutil.copy2(source, self._draft_path(scene, name))
        except OSError:
            # A failed park must not block the switch; the live file is intact
            # and that is what matters.
            pass

    def switch_draft(self, scene_id: str, name: str) -> str:
        scene = self.data.scene(scene_id)
        if not scene:
            raise ProjectError("That scene is no longer in the project.")
        current = scene.active_draft or "Main"
        if name == current:
            return name
        if name not in self.list_drafts(scene_id):
            raise ProjectError(f"'{name}' is not a draft of this scene.")

        self._store_draft(scene, current)
        target = self._draft_path(scene, name)
        if target.exists():
            try:
                shutil.copy2(target, self.abs(scene.docx))
            except OSError as exc:
                raise ProjectError(
                    "Could not switch draft - the document may be open in Word."
                ) from exc
        else:
            # The branch was recorded but its file is gone. Start it empty
            # rather than silently leaving the previous branch's text in place
            # and letting the writer think they switched.
            docxio.write_prose(
                self.abs(scene.docx), scene.title, "",
                font=settings["manuscript_font"],
                size=settings["manuscript_font_size"],
                line_spacing=settings["manuscript_line_spacing"],
                margin=settings["manuscript_margin"],
                first_line_indent=settings["manuscript_first_line_indent"],
            )
        scene.active_draft = name
        scene.word_count = docxio.docx_word_count(self.abs(scene.docx))
        scene.docx_mtime = docxio.docx_mtime(self.abs(scene.docx))
        scene.modified = now_iso()
        self.mark_dirty()
        return name

    def delete_draft(self, scene_id: str, name: str) -> None:
        scene = self.data.scene(scene_id)
        if not scene or name == (scene.active_draft or "Main"):
            raise ProjectError("You cannot delete the draft you are working in.")
        scene.drafts = [d for d in scene.drafts if d != name]
        try:
            self._draft_path(scene, name).unlink(missing_ok=True)
        except OSError:
            pass
        self.mark_dirty()

    def draft_summary(self, scene_id: str) -> List[Tuple[str, int, bool]]:
        """(name, words, is_active) for every branch of a scene."""
        scene = self.data.scene(scene_id)
        if not scene:
            return []
        active = scene.active_draft or "Main"
        out: List[Tuple[str, int, bool]] = []
        for name in self.list_drafts(scene_id):
            if name == active:
                words = scene.word_count
            else:
                path = self._draft_path(scene, name)
                words = docxio.docx_word_count(path) if path.exists() else 0
            out.append((name, words, name == active))
        return out

    # ------------------------------------------------------------------
    # Timeline
    # ------------------------------------------------------------------

    def add_event(self, title: str, story_date: str = "",
                  description: str = "", kind: str = "event") -> TimelineEvent:
        event = TimelineEvent(
            title=title, story_date=story_date, description=description,
            kind=kind, order=self.data.next_order(self.data.events),
        )
        event.sort_key = _date_sort_key(story_date, event.order)
        self.data.events.append(event)
        self.mark_dirty()
        return event

    def delete_event(self, event_id: str) -> None:
        self.data.events = [e for e in self.data.events if e.id != event_id]
        self.mark_dirty()

    def ordered_events(self) -> List[TimelineEvent]:
        return sorted(self.data.events, key=lambda e: (e.sort_key, e.order))

    # ------------------------------------------------------------------
    # Disk synchronisation
    # ------------------------------------------------------------------

    def sync_from_disk(self, force: bool = False) -> Tuple[int, int]:
        """
        Refresh cached word counts and sheet values for changed files only.

        Returns (scenes_updated, entities_updated).
        """
        scenes_updated = 0
        for scene in self.data.scenes:
            if not scene.docx:
                continue
            path = self.abs(scene.docx)
            mtime = docxio.docx_mtime(path)
            if not mtime:
                continue
            # Use `>` rather than `!=` so a clock skew or a coarse-resolution
            # volume cannot make us re-read the same file forever, and never
            # trust a read that failed.
            if force or mtime != scene.docx_mtime:
                if not docxio.prose_readable(path):
                    # Locked by Word, or a OneDrive placeholder still
                    # downloading. Keeping the cached count is far better than
                    # replacing a real number with a wrong zero.
                    continue
                scene.word_count = docxio.docx_word_count(path)
                scene.docx_mtime = mtime
                scenes_updated += 1

        entities_updated = 0
        for entity in self.data.entities:
            if not entity.docx:
                continue
            path = self.abs(entity.docx)
            mtime = docxio.docx_mtime(path)
            if not mtime:
                continue
            if force or mtime != entity.cache_mtime:
                fields = docxio.read_field_sheet(path)
                if not fields and not docxio.prose_readable(path):
                    continue          # unreadable, not empty - keep the cache
                entity.cache = fields
                entity.cache_mtime = mtime
                self._promote_entity_fields(entity)
                entities_updated += 1

        if scenes_updated or entities_updated:
            self.mark_dirty()
        return scenes_updated, entities_updated

    def missing_files(self) -> List[Tuple[str, str]]:
        """Anything the manifest points at that is no longer on disk."""
        missing: List[Tuple[str, str]] = []
        for scene in self.data.scenes:
            if scene.docx and not self.abs(scene.docx).exists():
                missing.append(("Scene", scene.title))
        for entity in self.data.entities:
            if entity.docx and not self.abs(entity.docx).exists():
                missing.append((entity.type.title(), entity.name))
        for note in self.data.notes:
            if note.docx and not self.abs(note.docx).exists():
                missing.append(("Note", note.title))
        return missing

    def import_loose_documents(self) -> int:
        """
        Adopt .docx files dropped into a chapter folder outside the tool.

        Lets you copy in existing work without retyping it.
        """
        known = {
            str(self.abs(s.docx).resolve()).lower()
            for s in self.data.scenes if s.docx
        }
        # Notes and entity sheets also live under the project; a chapter folder
        # should not adopt one that was moved there by accident.
        for other in list(self.data.entities) + list(self.data.notes):
            if other.docx:
                known.add(str(self.abs(other.docx).resolve()).lower())
        added = 0
        for chapter in self.data.ordered_chapters():
            if not chapter.folder:
                continue
            folder = self.abs(chapter.folder)
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob("*.docx")):
                if path.name.startswith("~$") or path.name.endswith(".tmp~"):
                    continue
                if str(path.resolve()).lower() in known:
                    continue
                known.add(str(path.resolve()).lower())
                order = self.data.next_order(self.data.scenes_in(chapter.id))
                scene = Scene(
                    title=path.stem, chapter_id=chapter.id, order=order,
                    docx=self.rel(path), status="Draft",
                )
                scene.word_count = docxio.docx_word_count(path)
                scene.docx_mtime = docxio.docx_mtime(path)
                self.data.scenes.append(scene)
                added += 1
        if added:
            self.mark_dirty()
        return added

    # ------------------------------------------------------------------
    # Sweeps (explicit commands - never automatic)
    # ------------------------------------------------------------------

    def collect_bracket_tags(self) -> List[Tuple[str, str, str]]:
        """
        Find every [bracket tag] across scenes and notes.

        Returns (where, tag, context). This is the Fix Later queue: drop a
        [check the date] while drafting and keep going.
        """
        found: List[Tuple[str, str, str]] = []
        for scene in self.data.ordered_scenes():
            if not scene.docx:
                continue
            text = docxio.read_prose(self.abs(scene.docx))
            for para in text.split("\n\n"):
                for match in BRACKET_TAG.finditer(para):
                    tag = match.group(1).strip()
                    if tag.lower().startswith("synopsis:"):
                        continue
                    start = max(0, match.start() - 60)
                    context = para[start:match.end() + 60].replace("\n", " ")
                    found.append((scene.title, tag, context.strip()))
        return found

    def find_mentions(self, entity_id: str) -> List[Tuple[str, int]]:
        """Which scenes mention an entity by name or alias, and how often."""
        entity = self.data.entity(entity_id)
        if not entity:
            return []
        names = entity.all_names()
        if not names:
            return []
        pattern = re.compile(
            r"\b(" + "|".join(re.escape(n) for n in names) + r")\b", re.IGNORECASE
        )
        hits: List[Tuple[str, int]] = []
        for scene in self.data.ordered_scenes():
            if not scene.docx:
                continue
            text = docxio.read_prose(self.abs(scene.docx))
            count = len(pattern.findall(text))
            if count:
                hits.append((scene.title, count))
        return hits

    # ------------------------------------------------------------------
    # Find and replace across the whole project
    # ------------------------------------------------------------------

    #: What replace is allowed to touch. Kept separate so renaming a character
    #: in the prose does not silently rewrite unrelated research notes.
    REPLACE_SCOPES = ("manuscript", "notes", "sheets", "cards", "names")

    @staticmethod
    def build_pattern(needle: str, match_case: bool = False,
                      whole_word: bool = True,
                      regex: bool = False) -> "re.Pattern":
        """
        The one place a search pattern is built, so find and replace agree.

        Whole word is on by default: replacing "Ada" without it turns
        "Adamant" into "<new>mant", and on a 300,000 word manuscript nobody
        finds that until the proof copy arrives.
        """
        body = needle if regex else re.escape(needle)
        if whole_word and not regex:
            body = r"\b" + body + r"\b"
        return re.compile(body, 0 if match_case else re.IGNORECASE)

    def preview_replace(self, needle: str, replacement: str, *,
                        scopes: Sequence[str] = REPLACE_SCOPES,
                        match_case: bool = False, whole_word: bool = True,
                        regex: bool = False, limit: int = 400
                        ) -> List[Tuple[str, str, int, str]]:
        """
        What a replace would do, without doing any of it.

        Returns (kind, label, count, sample) rows. Nothing is written and no
        document is opened for writing, so this is safe to run while the
        writer is still deciding.
        """
        pattern = self.build_pattern(needle, match_case, whole_word, regex)
        rows: List[Tuple[str, str, int, str]] = []

        def sample(text: str) -> str:
            match = pattern.search(text)
            if not match:
                return ""
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            snippet = text[start:end].replace("\n", " ")
            return ("..." if start else "") + snippet + \
                   ("..." if end < len(text) else "")

        if "manuscript" in scopes:
            for scene in self.data.ordered_scenes():
                if not scene.docx:
                    continue
                path = self.abs(scene.docx)
                if not path.exists():
                    continue
                count = docxio.count_in_document(path, pattern)
                if count:
                    rows.append(("Scene", scene.display, count,
                                 sample(docxio.read_prose(path))))
        if "notes" in scopes:
            for note in self.data.notes:
                if not note.docx:
                    continue
                path = self.abs(note.docx)
                if not path.exists():
                    continue
                count = docxio.count_in_document(path, pattern)
                if count:
                    rows.append(("Note", note.title, count,
                                 sample(docxio.read_prose(path))))
        if "sheets" in scopes:
            for entity in self.data.entities:
                if not entity.docx:
                    continue
                path = self.abs(entity.docx)
                if not path.exists():
                    continue
                count = docxio.count_in_document(path, pattern)
                if count:
                    rows.append((ENTITY_LABELS.get(entity.type, "Sheet"),
                                 entity.name, count,
                                 sample(" ".join(entity.cache.values()))))
        if "cards" in scopes:
            for scene in self.data.ordered_scenes():
                blob = " ".join([scene.synopsis, scene.notes, scene.goal,
                                 scene.conflict, scene.disaster,
                                 scene.reaction, scene.dilemma,
                                 scene.decision, scene.value_start,
                                 scene.value_end])
                count = len(pattern.findall(blob))
                if count:
                    rows.append(("Scene card", scene.display, count,
                                 sample(blob)))
            for chapter in self.data.ordered_chapters():
                blob = f"{chapter.synopsis} {chapter.notes}"
                count = len(pattern.findall(blob))
                if count:
                    rows.append(("Chapter card", chapter.display, count,
                                 sample(blob)))
        if "names" in scopes:
            for entity in self.data.entities:
                blob = " ".join([entity.name, entity.summary]
                                + list(entity.aliases))
                count = len(pattern.findall(blob))
                if count:
                    rows.append(("Name", entity.name, count, sample(blob)))
        return rows[:limit]

    def replace_everywhere(self, needle: str, replacement: str, *,
                           scopes: Sequence[str] = REPLACE_SCOPES,
                           match_case: bool = False, whole_word: bool = True,
                           regex: bool = False
                           ) -> Tuple[int, int, List[Tuple[str, str]]]:
        """
        Do it. Returns (replacements, documents changed, problems).

        Every document is snapshotted before it is touched, so File > Versions
        can put any of them back one at a time. The manifest half of the
        change goes on the undo stack with everything else.

        A document that is open in Word is reported rather than forced: the
        rest of the replace still happens, and the writer is told which files
        to close and run it again.
        """
        if not needle:
            return 0, 0, []
        pattern = self.build_pattern(needle, match_case, whole_word, regex)
        replaced = 0
        documents = 0
        problems: List[Tuple[str, str]] = []

        def sweep(path: Path, label: str) -> None:
            nonlocal replaced, documents
            if not path.exists():
                return
            try:
                if docxio.count_in_document(path, pattern) == 0:
                    return
                keep_rolling_copy(path)
                from . import backup

                backup.snapshot_document(self, path, label)
                count = docxio.replace_in_document(path, pattern, replacement)
            except Exception as exc:
                problems.append((label, str(exc)))
                return
            if count:
                replaced += count
                documents += 1

        if "manuscript" in scopes:
            for scene in self.data.ordered_scenes():
                if scene.docx:
                    sweep(self.abs(scene.docx), scene.display)
        if "notes" in scopes:
            for note in self.data.notes:
                if note.docx:
                    sweep(self.abs(note.docx), note.title)
        if "sheets" in scopes:
            for entity in self.data.entities:
                if entity.docx:
                    sweep(self.abs(entity.docx), entity.name)

        # Metadata lives in the manifest, so it is covered by undo.
        def swap(value: str) -> str:
            nonlocal replaced
            new_value, count = pattern.subn(replacement, value or "")
            replaced += count
            return new_value

        if "cards" in scopes:
            for scene in self.data.scenes:
                for field_name in ("synopsis", "notes", "goal", "conflict",
                                   "disaster", "reaction", "dilemma",
                                   "decision", "value_start", "value_end"):
                    setattr(scene, field_name, swap(getattr(scene, field_name)))
            for chapter in self.data.chapters:
                chapter.synopsis = swap(chapter.synopsis)
                chapter.notes = swap(chapter.notes)
        if "names" in scopes:
            for entity in self.data.entities:
                entity.name = swap(entity.name)
                entity.summary = swap(entity.summary)
                entity.aliases = [swap(a) for a in entity.aliases]

        # The word counts in the manifest are now stale wherever a document
        # changed length - "Ada" to "Adalind" across 400 scenes moves the
        # total. Re-reading is cheaper than being wrong about it.
        if documents:
            for scene in self.data.scenes:
                if scene.docx:
                    path = self.abs(scene.docx)
                    if path.exists():
                        scene.word_count = docxio.docx_word_count(path)
                        scene.docx_mtime = docxio.docx_mtime(path)

        if replaced:
            self.mark_dirty()
        return replaced, documents, problems

    def search(self, needle: str, limit: int = 200) -> List[Tuple[str, str, str]]:
        """
        Full-text search across scenes, sheets and notes.

        Returns (kind, name, snippet).
        """
        needle = needle.strip()
        if len(needle) < 2:
            return []
        pattern = re.compile(re.escape(needle), re.IGNORECASE)
        results: List[Tuple[str, str, str]] = []

        def snippet(text: str) -> str:
            match = pattern.search(text)
            if not match:
                return ""
            start = max(0, match.start() - 70)
            return ("..." if start else "") + \
                text[start:match.end() + 70].replace("\n", " ").strip() + "..."

        for scene in self.data.ordered_scenes():
            if len(results) >= limit:
                return results
            haystack = "\n".join([scene.title, scene.synopsis, scene.notes,
                                  scene.goal, scene.conflict, scene.disaster])
            if pattern.search(haystack):
                results.append(("Scene", scene.title, snippet(haystack)))
                continue
            if scene.docx:
                text = docxio.read_prose(self.abs(scene.docx))
                if pattern.search(text):
                    results.append(("Scene", scene.title, snippet(text)))

        for entity in self.data.entities:
            if len(results) >= limit:
                return results
            fields = self.entity_fields(entity.id, refresh=False)
            haystack = "\n".join([entity.name, entity.summary] + list(fields.values()))
            if pattern.search(haystack):
                label = entity.type.title()
                results.append((label, entity.name, snippet(haystack)))

        for note in self.data.notes:
            if len(results) >= limit:
                return results
            if not note.docx:
                continue
            text = docxio.read_prose(self.abs(note.docx))
            if pattern.search(note.title) or pattern.search(text):
                results.append(("Note", note.title, snippet(text or note.title)))

        return results

    # ------------------------------------------------------------------
    # Document generation
    # ------------------------------------------------------------------

    def generate_planning_docs(self) -> None:
        outline = self.folder("outline")
        docxio.write_field_sheet(
            outline / "Premise & Logline.docx",
            "Premise & Logline",
            templates.PREMISE,
            subtitle=self.data.title,
            kicker="FOUNDATION",
            note="Fill this in before drafting. Come back and revise it - "
                 "the premise you finish with is rarely the one you start with.",
        )
        docxio.write_field_sheet(
            self.folder("notes") / "Why Compass.docx",
            "Why Compass",
            templates.WHY_COMPASS,
            subtitle="Read this on the bad days",
            kicker="MOTIVATION",
            note="This document exists for the week in month four when you are "
                 "certain the book is worthless. It will not feel worthless "
                 "forever.",
        )

    def generate_world_bible(self, packs: Sequence[str] = ()) -> None:
        world = self.folder("world")
        skip = set()
        if "fantasy" not in packs:
            # Still written, but flagged as optional in its subtitle.
            pass
        for stem, (title, subtitle, sections) in templates.WORLD_BIBLE_DOCS.items():
            if stem in skip:
                continue
            docxio.write_field_sheet(
                world / f"{safe_filename(stem)}.docx",
                title, sections, subtitle=subtitle, kicker="WORLD BIBLE",
            )
        docxio.write_field_sheet(
            self.folder("continuity") / "Series Continuity.docx",
            "Series Continuity",
            templates.SERIES_CONTINUITY,
            subtitle="Established facts, so book two does not contradict book one",
            kicker="CONTINUITY",
            note="Record a fact here the moment it appears on the page. "
                 "This document is cheaper than a rewrite.",
        )

    def generate_publishing_docs(self) -> None:
        pub = self.folder("publishing")
        docxio.write_field_sheet(
            pub / "Query Letter.docx", "Query Letter",
            templates.QUERY_LETTER,
            subtitle="Hook, Book, Cook", kicker="SUBMISSION",
            note="Under 350 words. The hook does the work; the bio does not.",
        )
        docxio.write_field_sheet(
            pub / "Synopsis.docx", "Synopsis",
            templates.SYNOPSIS_SHEET,
            subtitle="Present tense, third person, spoils the ending",
            kicker="SUBMISSION",
        )
        docxio.write_field_sheet(
            pub / "Beta Reader Questionnaire.docx",
            "Beta Reader Questionnaire",
            templates.BETA_QUESTIONNAIRE,
            subtitle="One copy per reader",
            kicker="FEEDBACK",
            note="Send the same four questions to everyone. When three readers "
                 "flag the same chapter, that chapter is the problem.",
        )
        self._write_submission_tracker(pub / "Submission Tracker.docx")

    def _write_submission_tracker(self, path: Path) -> None:
        doc = docxio.sheet_document()
        docxio.add_title_block(
            doc, "Submission Tracker",
            "Where it went, when, and what came back", "SUBMISSION",
        )
        docxio.add_note(
            doc, "Log every submission. Track response times so you know when "
                 "a query has gone quiet rather than wondering.",
        )
        docxio.add_data_table(
            doc,
            ["Agent / Market", "Date sent", "Materials", "Response due",
             "Reply", "Notes"],
            [["", "", "", "", "", ""] for _ in range(18)],
            widths=[1.6, 0.85, 1.15, 0.95, 0.85, 1.3],
        )
        from .atomic import save_via_atomic

        save_via_atomic(path, doc.save)

    def generate_reference_docs(self, packs: Sequence[str] = ()) -> None:
        notes = self.folder("notes")
        self._write_revision_checklist(notes / "Revision Checklist.docx")
        self._write_dialogue_rules(notes / "Dialogue Rules.docx")
        self._write_block_diagnostic(notes / "Writers Block Diagnostic.docx")
        self._write_scene_card(notes / "Scene Card (blank).docx")
        if "mystery" in packs:
            self._write_clue_tracker(self.folder("threads") / "Clue Tracker.docx")
        if "romance" in packs:
            self._write_relationship_tracker(
                self.folder("threads") / "Relationship Arc Tracker.docx"
            )
        self.write_timeline_doc()

    def _write_revision_checklist(self, path: Path) -> None:
        doc = docxio.sheet_document()
        docxio.add_title_block(
            doc, "Revision Checklist",
            "Four passes, in this order. Never mix them.", "REVISION",
        )
        docxio.add_note(
            doc, "Doing these simultaneously is why revision feels impossible. "
                 "Structure first; typos last.",
        )
        for _key, title, items in structures.REVISION_TIERS:
            doc.add_heading(title, level=2)
            docxio.add_checklist(doc, items)
        from .atomic import save_via_atomic

        save_via_atomic(path, doc.save)

    def _write_dialogue_rules(self, path: Path) -> None:
        doc = docxio.sheet_document()
        docxio.add_title_block(
            doc, "Dialogue Rules", "US convention (Chicago Manual of Style)",
            "REFERENCE",
        )
        for rule, detail in templates.DIALOGUE_RULES:
            doc.add_heading(rule, level=3)
            para = doc.add_paragraph(detail)
            para.paragraph_format.space_after = docxio.Pt(8)
        from .atomic import save_via_atomic

        save_via_atomic(path, doc.save)

    def _write_block_diagnostic(self, path: Path) -> None:
        doc = docxio.sheet_document()
        docxio.add_title_block(
            doc, "Writer's Block Diagnostic",
            "Five causes. The fix depends entirely on which one you have.",
            "DIAGNOSTIC",
        )
        docxio.add_note(
            doc, "Most blocks are physiological, not moral. Answer the "
                 "diagnostic question honestly and apply the matching fix.",
        )
        docxio.add_data_table(
            doc,
            ["Type", "Share", "Root cause", "Diagnostic question",
             "The fix", "Timeline"],
            [
                [b.name, b.share, b.root_cause, b.question, b.fix, b.timeline]
                for b in structures.BLOCK_TYPES
            ],
            widths=[0.95, 0.5, 1.25, 1.6, 1.5, 0.85],
        )
        for block in structures.BLOCK_TYPES:
            doc.add_heading(f"{block.name} - what to actually do", level=3)
            docxio.add_checklist(doc, block.interventions)
        from .atomic import save_via_atomic

        save_via_atomic(path, doc.save)

    def _write_scene_card(self, path: Path) -> None:
        docxio.write_field_sheet(
            path, "Scene Card", templates.SCENE_CARD,
            subtitle="Print or duplicate one per scene",
            kicker="PLANNING",
            note="A scene that cannot fill in Goal, Conflict and Disaster - or "
                 "Reaction, Dilemma and Decision - is probably not yet a scene.",
        )

    def _write_clue_tracker(self, path: Path) -> None:
        doc = docxio.sheet_document()
        docxio.add_title_block(
            doc, "Clue Tracker", "Play fair with the reader", "MYSTERY",
        )
        docxio.add_note(
            doc, "Every clue the detective sees, the reader must see. Log the "
                 "scene where each clue is planted and where it pays off.",
        )
        docxio.add_data_table(
            doc,
            ["Clue", "True or red herring", "Planted in", "Who notices",
             "Paid off in", "Reader can deduce?"],
            [["", "", "", "", "", ""] for _ in range(20)],
            widths=[1.5, 1.0, 1.0, 1.0, 1.0, 1.15],
        )
        from .atomic import save_via_atomic

        save_via_atomic(path, doc.save)

    def _write_relationship_tracker(self, path: Path) -> None:
        doc = docxio.sheet_document()
        docxio.add_title_block(
            doc, "Relationship Arc Tracker",
            "Track both leads beat by beat", "ROMANCE",
        )
        beats = structures.framework("romance_beat").beats
        docxio.add_data_table(
            doc,
            ["Beat", "Scene", "Lead A feels", "Lead B feels", "What changes"],
            [[b.name, "", "", "", ""] for b in beats],
            widths=[1.7, 1.0, 1.35, 1.35, 1.25],
        )
        from .atomic import save_via_atomic

        save_via_atomic(path, doc.save)

    def write_outline_doc(self) -> Path:
        """The beat sheet: the chosen framework with your answers and targets."""
        framework = structures.framework(self.data.structure)
        total = self.data.targets.total_words
        doc = docxio.sheet_document()
        docxio.add_title_block(
            doc, "Outline", f"{framework.name} - {self.data.title}", "STRUCTURE",
        )
        docxio.add_note(doc, framework.note)
        docxio.add_note(doc, f"Source: {framework.source}")
        docxio.add_divider(doc)

        rows = []
        for beat in sorted(self.data.beats, key=lambda b: b.order):
            target = beat.target_word(total)
            scenes = ", ".join(
                (self.data.scene(sid).title if self.data.scene(sid) else "?")
                for sid in beat.scene_ids
            )
            rows.append([
                beat.name,
                f"{int(beat.pct * 100)}%" if beat.pct is not None else "-",
                f"{target:,}" if target else "-",
                beat.answer or beat.prompt,
                scenes,
                "yes" if beat.done else "",
            ])
        docxio.add_data_table(
            doc,
            ["Beat", "At", "Word", "Plan / prompt", "Scenes", "Done"],
            rows,
            widths=[1.5, 0.4, 0.65, 2.75, 1.15, 0.45],
        )

        doc.add_heading("Chapter & Scene Outline", level=2)
        scene_rows = []
        for chapter in self.data.ordered_chapters():
            scene_rows.append([chapter.title.upper(), "", "", "", ""])
            for scene in self.data.scenes_in(chapter.id):
                pov = self.data.entity(scene.pov_id)
                scene_rows.append([
                    f"    {scene.title}",
                    pov.name if pov else "",
                    scene.status,
                    f"{scene.word_count:,}",
                    scene.synopsis,
                ])
        if scene_rows:
            docxio.add_data_table(
                doc, ["Chapter / Scene", "POV", "Status", "Words", "Synopsis"],
                scene_rows, widths=[1.9, 0.95, 0.8, 0.6, 2.65],
            )

        from .atomic import save_via_atomic

        return save_via_atomic(self.folder("outline") / "Outline.docx", doc.save)

    def write_timeline_doc(self) -> Path:
        doc = docxio.sheet_document()
        docxio.add_title_block(
            doc, "Timeline", self.data.title, "CHRONOLOGY",
        )
        docxio.add_note(
            doc, "Story order and chronological order are different things. "
                 "This document is chronological; the manuscript is not.",
        )
        events = self.ordered_events()
        rows = []
        for event in events:
            chars = ", ".join(
                (self.data.entity(cid).name if self.data.entity(cid) else "?")
                for cid in event.character_ids
            )
            location = self.data.entity(event.location_id)
            scene = self.data.scene(event.scene_id)
            rows.append([
                event.story_date, event.title, event.kind,
                chars, location.name if location else "",
                scene.title if scene else "",
                "on page" if event.on_page else "backstory",
            ])
        if not rows:
            rows = [["", "", "", "", "", "", ""] for _ in range(12)]
        docxio.add_data_table(
            doc,
            ["When", "Event", "Kind", "Who", "Where", "Scene", "Visibility"],
            rows,
            widths=[0.85, 1.85, 0.65, 1.2, 0.95, 1.0, 0.8],
        )
        from .atomic import save_via_atomic

        return save_via_atomic(self.folder("timeline") / "Timeline.docx", doc.save)

    def write_fix_later_doc(self) -> Tuple[Path, int]:
        """Sweep the manuscript for [bracket tags] and collect them into one file."""
        tags = self.collect_bracket_tags()
        doc = docxio.sheet_document()
        docxio.add_title_block(
            doc, "Fix Later", f"{len(tags)} open tags", "QUEUE",
        )
        docxio.add_note(
            doc, "Drop [tags] while drafting instead of stopping to research. "
                 "Sweep them here when you are in editing mode.",
        )
        if tags:
            docxio.add_data_table(
                doc, ["Scene", "Tag", "Context"],
                [[where, tag, context] for where, tag, context in tags],
                widths=[1.4, 1.6, 3.6],
            )
        else:
            doc.add_paragraph("No open tags. Either you are very disciplined "
                              "or you have not started yet.")
        from .atomic import save_via_atomic

        path = save_via_atomic(self.folder("notes") / "Fix Later.docx", doc.save)
        return path, len(tags)

    def write_reverse_outline(self) -> Path:
        """
        Build an outline FROM the draft - what you actually wrote.

        Comparing this against Outline.docx is the fastest structural edit
        available: it shows drift without you having to reread the book.
        """
        doc = docxio.sheet_document()
        docxio.add_title_block(
            doc, "Reverse Outline",
            "Generated from the current draft", "DIAGNOSTIC",
        )
        docxio.add_note(
            doc, "Compare this with your Outline. Where they disagree is "
                 "either a discovery worth keeping or drift worth fixing.",
        )
        total = max(1, self.data.compiled_word_count)
        running = 0
        rows = []
        for chapter in self.data.ordered_chapters():
            for scene in self.data.scenes_in(chapter.id):
                running += scene.word_count
                pov = self.data.entity(scene.pov_id)
                shift = ""
                if scene.value_start or scene.value_end:
                    shift = f"{scene.value_start} -> {scene.value_end}"
                rows.append([
                    chapter.title, scene.title,
                    pov.name if pov else "",
                    f"{scene.word_count:,}",
                    f"{running * 100 // total}%",
                    scene.synopsis,
                    shift,
                    scene.disaster or scene.decision,
                ])
        docxio.add_data_table(
            doc,
            ["Chapter", "Scene", "POV", "Words", "At", "What happens",
             "Value shift", "Disaster / decision"],
            rows or [["", "", "", "", "", "", "", ""]],
            widths=[0.95, 1.15, 0.7, 0.5, 0.4, 1.7, 1.0, 1.2],
        )
        from .atomic import save_via_atomic

        return save_via_atomic(
            self.folder("outline") / "Reverse Outline.docx", doc.save
        )


# ==========================================================================
# Module helpers
# ==========================================================================


def _date_sort_key(story_date: str, fallback: int) -> float:
    """
    Turn a hand-written in-world date into something sortable.

    Handles "Day 12", "1247", "3rd of Harvest", "1247-03-04" and gives up
    gracefully to insertion order when it cannot find a number.
    """
    if not story_date:
        return float(fallback)
    numbers = re.findall(r"\d+", story_date)
    if not numbers:
        return float(fallback)
    key = 0.0
    for i, chunk in enumerate(numbers[:3]):
        # Truncated to 12 digits: int() on an arbitrarily long digit run would
        # raise OverflowError converting to float, and no in-world date needs
        # more precision than a trillion.
        try:
            value = int(chunk[:12])
        except ValueError:
            continue
        key += value / (1000.0 ** i)
    return key


def list_projects(parent: Optional[Path] = None) -> List[Tuple[str, Path]]:
    """Every project folder under Projects, as (title, path)."""
    parent = Path(parent) if parent else projects_root()
    found: List[Tuple[str, Path]] = []
    if not parent.exists():
        return found
    for child in sorted(parent.iterdir()):
        manifest = child / MANIFEST_NAME
        if not manifest.is_file():
            continue
        raw = read_json(manifest, {}) or {}
        title = raw.get("title") or child.name
        found.append((title, child))
    return found
