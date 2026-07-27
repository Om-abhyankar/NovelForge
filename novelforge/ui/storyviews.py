"""
The windows that sit on top of the story graph.

Four separate windows rather than one crowded one, because each answers a
different question and you want them open at different moments:

    StoryGraphWindow    what is in this book, and what is wrong with it
    IdeaInboxWindow     catch a thought now, decide where it goes later
    DraftsDialog        try a different version of this scene
    NoteLinksDialog     attach research to the thing it is research for

Everything here is read-mostly and cheap: the graph is built once per window
and reused, and the graph itself is cached between windows.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .. import storygraph
from ..config import THEMES, open_in_default_app, settings
from ..model import ENTITY_LABELS
from .dialogs import Dialog
from .widgets import ScrolledText, center_window


def _monospace(widget: ScrolledText) -> None:
    theme = THEMES.get(settings["theme"], THEMES["warm"])
    widget.text.configure(
        background=theme["bg"], foreground=theme["fg"],
        insertbackground=theme["caret"], selectbackground=theme["select"],
    )


def build_graph_with_progress(parent, project):
    """
    Build the story graph, showing a bar if it is going to take a while.

    A small novel builds in a fraction of a second and the window never
    appears; a 300,000 word one takes about twenty-five seconds the first
    time, and silence for that long reads as a hang. The bar is only created
    once the read is already under way, so the common case costs nothing.
    """
    cached = storygraph.cached_graph(project)
    if cached is not None:
        return cached

    state: Dict[str, Any] = {"window": None, "bar": None, "label": None}

    def report(done: int, total: int) -> None:
        if state["window"] is None:
            if total < 60:
                return          # fast enough that a dialog would only flicker
            window = tk.Toplevel(parent)
            window.title("Reading the manuscript")
            window.transient(parent)
            window.resizable(False, False)
            frame = ttk.Frame(window, padding=16)
            frame.grid(row=0, column=0, sticky="nsew")
            state["label"] = ttk.Label(
                frame, text="Reading the manuscript...", width=44)
            state["label"].grid(row=0, column=0, sticky="w", pady=(0, 8))
            ttk.Label(
                frame,
                text="This happens once. Afterwards it is instant until you "
                     "edit something.",
                wraplength=320, justify="left", style="Hint.TLabel",
            ).grid(row=2, column=0, sticky="w", pady=(8, 0))
            state["bar"] = ttk.Progressbar(frame, length=320, maximum=total)
            state["bar"].grid(row=1, column=0, sticky="ew")
            center_window(window, 380, 150)
            window.update()
            state["window"] = window
        if state["window"] is not None:
            state["bar"]["value"] = done
            state["label"].configure(text=f"Reading scene {done:,} of {total:,}")
            state["window"].update()

    try:
        return storygraph.build(project, progress=report)
    finally:
        if state["window"] is not None:
            try:
                state["window"].destroy()
            except Exception:
                pass
        parent.update_idletasks()


def scrolled(parent, widget_factory, row: int = 0, column: int = 0):
    """
    Put a list or tree in a frame with a scrollbar and return it.

    Every list in this application can grow past the window: a novel has
    hundreds of scenes and a squeezed window has room for eight. Without this
    the rest are simply unreachable.
    """
    holder = ttk.Frame(parent)
    holder.grid(row=row, column=column, sticky="nsew")
    holder.rowconfigure(0, weight=1)
    holder.columnconfigure(0, weight=1)
    widget = widget_factory(holder)
    widget.grid(row=0, column=0, sticky="nsew")
    bar = ttk.Scrollbar(holder, orient="vertical", command=widget.yview)
    bar.grid(row=0, column=1, sticky="ns")
    widget.configure(yscrollcommand=bar.set)
    return widget


# ==========================================================================
# The story graph window
# ==========================================================================


class StoryGraphWindow(tk.Toplevel):
    """
    Everything the graph knows, in four tabs.

    Non-modal on purpose: the whole point of the continuity tab is to have it
    open beside the manuscript while you fix what it found.
    """

    def __init__(self, parent, project, start_tab: str = "") -> None:
        super().__init__(parent)
        self.project = project
        self.title(f"Story Graph - {project.data.title}")
        self.graph = build_graph_with_progress(parent, project)

        container = ttk.Frame(self, padding=8)
        container.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(container)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        self.views: Dict[str, ScrolledText] = {}
        for key, label in [("overview", "Overview"),
                           ("continuity", "Continuity"),
                           ("relationships", "Relationships")]:
            frame = ttk.Frame(self.notebook, padding=6)
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)
            view = ScrolledText(frame, height=28, wrap="none",
                                font=("Consolas", 10))
            view.grid(row=0, column=0, sticky="nsew")
            _monospace(view)
            view.set_readonly(True)
            self.views[key] = view
            self.notebook.add(frame, text=label)

        self._build_ask_tab()

        bar = ttk.Frame(container)
        bar.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(bar, text="Refresh", command=self.refresh).grid(
            row=0, column=0, padx=(0, 6))
        ttk.Button(bar, text="Write Story Bible",
                   command=self.cmd_story_bible).grid(row=0, column=1,
                                                      padx=(0, 6))
        ttk.Button(bar, text="Copy this tab",
                   command=self._copy).grid(row=0, column=2, padx=(0, 6))
        bar.columnconfigure(3, weight=1)
        ttk.Button(bar, text="Close", command=self.destroy).grid(
            row=0, column=4, sticky="e")

        self.refresh()
        center_window(self, 940, 680, min_width=620, min_height=420)
        self.bind("<Escape>", lambda _e: self.destroy())
        if start_tab:
            self.show_tab(start_tab)

    # -- the question tab ------------------------------------------------
    def _build_ask_tab(self) -> None:
        frame = ttk.Frame(self.notebook, padding=6)
        frame.rowconfigure(3, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text="Ask about your own book. This searches the graph and the "
                 "manuscript on this machine - it never invents anything and "
                 "never sends your writing anywhere.",
            wraplength=860, justify="left", style="Hint.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        row = ttk.Frame(frame)
        row.grid(row=1, column=0, sticky="ew")
        row.columnconfigure(0, weight=1)
        self.question = ttk.Entry(row)
        self.question.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.question.bind("<Return>", lambda _e: self.cmd_ask())
        ttk.Button(row, text="Ask", command=self.cmd_ask).grid(row=0, column=1)

        examples = ttk.Frame(frame)
        examples.grid(row=2, column=0, sticky="w", pady=(6, 6))
        for index, text in enumerate(storygraph.SUGGESTED_QUESTIONS):
            ttk.Button(
                examples, text=text,
                command=lambda t=text: self._prefill(t),
            ).grid(row=index // 3, column=index % 3, padx=(0, 4), pady=2,
                   sticky="w")

        self.answer_view = ScrolledText(frame, height=20, wrap="word",
                                        font=("Consolas", 10))
        self.answer_view.grid(row=3, column=0, sticky="nsew")
        _monospace(self.answer_view)
        self.answer_view.set_readonly(True)
        self.notebook.add(frame, text="Ask")

    def _prefill(self, text: str) -> None:
        self.question.delete(0, "end")
        self.question.insert(0, text)
        self.question.focus_set()
        if "<" not in text:
            self.cmd_ask()

    def cmd_ask(self) -> None:
        question = self.question.get().strip()
        if not question:
            return
        reply = storygraph.answer(self.project, self.graph, question)
        self.answer_view.set_readonly(False)
        self.answer_view.set_value(reply)
        self.answer_view.set_readonly(True)

    # -- the report tabs -------------------------------------------------
    def refresh(self) -> None:
        self.graph = build_graph_with_progress(self, self.project)
        issues = storygraph.check_continuity(self.project, self.graph)
        bodies = {
            "overview": storygraph.overview_text(self.project, self.graph),
            "continuity": storygraph.continuity_text(self.project, issues),
            "relationships": storygraph.relationship_timeline_text(
                self.project, self.graph),
        }
        for key, body in bodies.items():
            view = self.views[key]
            view.set_readonly(False)
            view.set_value(body)
            view.set_readonly(True)

    def show_tab(self, key: str) -> None:
        order = ["overview", "continuity", "relationships", "ask"]
        if key in order:
            self.notebook.select(order.index(key))
            if key == "ask":
                self.question.focus_set()

    def _current_body(self) -> str:
        index = self.notebook.index("current")
        if index == 3:
            return self.answer_view.get_value()
        return list(self.views.values())[index].get_value()

    def _copy(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self._current_body())

    def cmd_story_bible(self) -> None:
        try:
            path = storygraph.write_story_bible(self.project, self.graph)
        except Exception as exc:
            messagebox.showerror("Could not write it", str(exc), parent=self)
            return
        if messagebox.askyesno(
            "Story Bible written",
            f"Written to:\n\n{path.name}\n\nOpen it now?",
            parent=self,
        ):
            open_in_default_app(path)


# ==========================================================================
# Idea inbox
# ==========================================================================


class IdeaInboxWindow(tk.Toplevel):
    """
    Catch a thought without deciding anything about it.

    The cost of an idea is the interruption, so capture is one box and one key.
    Filing happens later, and the tool offers a shortlist of places it might
    belong - worked out by matching the idea's words against your scenes and
    characters, not by guessing.
    """

    def __init__(self, parent, project, on_change: Callable[[], None]) -> None:
        super().__init__(parent)
        self.project = project
        self.on_change = on_change
        self.title(f"Idea Inbox - {project.data.title}")
        self._suggestions: List[Tuple[str, str, float]] = []

        container = ttk.Frame(self, padding=10)
        container.grid(row=0, column=0, sticky="nsew")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        ttk.Label(
            container,
            text="Type it and press Enter. Decide where it goes another day.",
            style="Hint.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        capture = ttk.Frame(container)
        capture.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        capture.columnconfigure(0, weight=1)
        self.entry = ttk.Entry(capture, font=("Georgia", 11))
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.entry.bind("<Return>", lambda _e: self.cmd_capture())
        ttk.Button(capture, text="Catch it",
                   command=self.cmd_capture).grid(row=0, column=1)

        panes = ttk.PanedWindow(container, orient="horizontal")
        panes.grid(row=2, column=0, sticky="nsew")

        left = ttk.Frame(panes)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)
        ttk.Label(left, text="Ideas").grid(row=0, column=0, sticky="w")
        self.tree = scrolled(left, lambda holder: ttk.Treeview(
            holder, columns=("status",), show="tree headings",
            selectmode="browse"), row=1)
        self.tree.heading("#0", text="Idea")
        self.tree.heading("status", text="Status")
        self.tree.column("#0", width=380, minwidth=140)
        self.tree.column("status", width=80, minwidth=60, anchor="center")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._on_select())
        panes.add(left, weight=3)

        right = ttk.Frame(panes)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)
        ttk.Label(right, text="Where it might belong").grid(
            row=0, column=0, sticky="w")
        self.suggestions = scrolled(right, lambda holder: tk.Listbox(
            holder, activestyle="none", exportselection=False), row=1)
        ttk.Button(right, text="File it here",
                   command=self.cmd_file_here).grid(row=2, column=0,
                                                    sticky="ew", pady=(6, 0))
        panes.add(right, weight=2)

        bar = ttk.Frame(container)
        bar.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        for index, (label, command) in enumerate([
            ("Keep without filing", self.cmd_keep),
            ("Turn into a note", self.cmd_to_note),
            ("Discard", self.cmd_discard),
            ("Delete", self.cmd_delete),
        ]):
            ttk.Button(bar, text=label, command=command).grid(
                row=0, column=index, padx=(0, 6))
        bar.columnconfigure(4, weight=1)
        ttk.Button(bar, text="Close", command=self.destroy).grid(
            row=0, column=5, sticky="e")

        self.refresh()
        center_window(self, 900, 560, min_width=620, min_height=400)
        self.entry.focus_set()
        self.bind("<Escape>", lambda _e: self.destroy())

    # -- data ------------------------------------------------------------
    def refresh(self) -> None:
        self.tree.delete(*self.tree.get_children())
        ideas = sorted(self.project.data.ideas,
                       key=lambda i: (i.status != "new", i.created),
                       reverse=False)
        for idea in ideas:
            where = ""
            if idea.target_id:
                target = (self.project.data.entity(idea.target_id)
                          or self.project.data.scene(idea.target_id)
                          or self.project.data.chapter(idea.target_id))
                if target:
                    where = f"  -> {target.display}"
            self.tree.insert("", "end", iid=idea.id,
                             text=idea.summary + where,
                             values=(idea.status,))
        self.suggestions.delete(0, "end")
        self._suggestions = []

    def _selected(self) -> Optional[str]:
        selection = self.tree.selection()
        return selection[0] if selection else None

    def _on_select(self) -> None:
        idea_id = self._selected()
        self.suggestions.delete(0, "end")
        self._suggestions = []
        if not idea_id:
            return
        self._suggestions = self.project.suggest_placements(idea_id)
        if not self._suggestions:
            self.suggestions.insert(
                "end", "Nothing obvious - file it by hand.")
            return
        for _target_id, label, score in self._suggestions:
            self.suggestions.insert("end", f"{int(score * 100):>3}%  {label}")

    # -- actions ---------------------------------------------------------
    def cmd_capture(self) -> None:
        text = self.entry.get().strip()
        if not text:
            return
        idea = self.project.add_idea(text)
        self.entry.delete(0, "end")
        self.project.save()
        self.refresh()
        self.tree.selection_set(idea.id)
        self.on_change()

    def cmd_file_here(self) -> None:
        idea_id = self._selected()
        selection = self.suggestions.curselection()
        if not idea_id or not selection or not self._suggestions:
            messagebox.showinfo("Pick both",
                                "Choose an idea and a place for it.",
                                parent=self)
            return
        target_id = self._suggestions[selection[0]][0]
        self.project.set_idea_status(idea_id, "placed", target_id)
        self.project.save()
        self.refresh()
        self.on_change()

    def cmd_keep(self) -> None:
        idea_id = self._selected()
        if idea_id:
            self.project.set_idea_status(idea_id, "kept")
            self.project.save()
            self.refresh()

    def cmd_discard(self) -> None:
        idea_id = self._selected()
        if idea_id:
            self.project.set_idea_status(idea_id, "discarded")
            self.project.save()
            self.refresh()

    def cmd_delete(self) -> None:
        idea_id = self._selected()
        if not idea_id:
            return
        if messagebox.askyesno("Delete idea", "Remove it for good?",
                               parent=self):
            self.project.delete_idea(idea_id)
            self.project.save()
            self.refresh()
            self.on_change()

    def cmd_to_note(self) -> None:
        idea_id = self._selected()
        idea = self.project.data.idea(idea_id) if idea_id else None
        if not idea:
            return
        title = idea.summary[:60] or "Idea"
        note = self.project.add_note(title, kind="note", body=idea.text)
        if idea.target_id:
            self.project.set_note_links(note.id, [idea.target_id])
        self.project.set_idea_status(idea.id, "placed", idea.target_id)
        self.project.save()
        self.refresh()
        self.on_change()
        messagebox.showinfo("Note created",
                            f"'{title}' is now in Notes.", parent=self)


# ==========================================================================
# Branching drafts
# ==========================================================================


class DraftsDialog(Dialog):
    """
    Alternate versions of one scene.

    The live document is always the active draft, so nothing else in the tool
    has to know branches exist - compiling, word counts and backups all keep
    working on whichever version you are currently in.
    """

    def __init__(self, parent, project, scene_id: str) -> None:
        self.project = project
        self.scene_id = scene_id
        self.changed = False
        scene = project.data.scene(scene_id)
        super().__init__(parent, f"Drafts of {scene.display if scene else '?'}",
                         560, 420)

    def build(self, parent: ttk.Frame) -> None:
        ttk.Label(
            parent,
            text="Try a different version of this scene without copying the "
                 "project. Switching parks the version you are leaving and "
                 "brings the other one in - neither is ever lost.",
            wraplength=500, justify="left", style="Hint.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.listbox = scrolled(parent, lambda holder: tk.Listbox(
            holder, height=10, activestyle="none", exportselection=False),
            row=1)
        parent.rowconfigure(1, weight=1)
        self.listbox.bind("<Double-Button-1>", lambda _e: self.cmd_switch())

        row = ttk.Frame(parent)
        row.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        row.columnconfigure(0, weight=1)
        self.new_name = ttk.Entry(row)
        self.new_name.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.new_name.bind("<Return>", lambda _e: self.cmd_new())
        ttk.Button(row, text="New draft from this one",
                   command=self.cmd_new).grid(row=0, column=1)

        self._reload()

    def build_buttons(self, parent: ttk.Frame) -> None:
        ttk.Button(parent, text="Switch to selected",
                   command=self.cmd_switch).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(parent, text="Delete selected",
                   command=self.cmd_delete).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(parent, text="Close", command=self.on_cancel).grid(
            row=0, column=2)

    def _reload(self) -> None:
        self.listbox.delete(0, "end")
        self.rows = self.project.draft_summary(self.scene_id)
        for name, words, active in self.rows:
            mark = "* " if active else "  "
            self.listbox.insert("end", f"{mark}{name:<28s} {words:>7,} words")
        for index, (_n, _w, active) in enumerate(self.rows):
            if active:
                self.listbox.selection_set(index)

    def _pick(self) -> Optional[str]:
        selection = self.listbox.curselection()
        if not selection or not self.rows:
            messagebox.showinfo("Pick a draft", "Select one first.",
                                parent=self)
            return None
        return self.rows[selection[0]][0]

    def cmd_new(self) -> None:
        name = self.new_name.get().strip()
        if not name:
            messagebox.showinfo("Name it",
                                "Give the new draft a name first.", parent=self)
            return
        try:
            self.project.create_draft(self.scene_id, name)
        except Exception as exc:
            messagebox.showerror("Could not create it", str(exc), parent=self)
            return
        self.new_name.delete(0, "end")
        self.changed = True
        self.project.save()
        self._reload()

    def cmd_switch(self) -> None:
        name = self._pick()
        if not name:
            return
        try:
            self.project.switch_draft(self.scene_id, name)
        except Exception as exc:
            messagebox.showerror("Could not switch", str(exc), parent=self)
            return
        self.changed = True
        self.project.save()
        self._reload()

    def cmd_delete(self) -> None:
        name = self._pick()
        if not name:
            return
        if not messagebox.askyesno(
            "Delete draft",
            f"Delete the draft '{name}'? Its text goes with it.",
            parent=self,
        ):
            return
        try:
            self.project.delete_draft(self.scene_id, name)
        except Exception as exc:
            messagebox.showerror("Could not delete", str(exc), parent=self)
            return
        self.changed = True
        self.project.save()
        self._reload()

    def on_cancel(self) -> None:
        self.result = self.changed
        self.destroy()


# ==========================================================================
# Research linking
# ==========================================================================


class NoteLinksDialog(Dialog):
    """Attach a note to the scenes and people it is actually about."""

    def __init__(self, parent, project, note_id: str) -> None:
        self.project = project
        self.note_id = note_id
        note = project.data.note(note_id)
        super().__init__(parent,
                         f"Link '{note.title if note else '?'}' to...", 600, 520)

    def build(self, parent: ttk.Frame) -> None:
        ttk.Label(
            parent,
            text="Pick everything this note is research for. It will then show "
                 "up on those scenes and characters, instead of being lost in "
                 "a folder.",
            wraplength=540, justify="left", style="Hint.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self.listbox = scrolled(parent, lambda holder: tk.Listbox(
            holder, height=18, selectmode="extended", activestyle="none",
            exportselection=False), row=1)
        parent.rowconfigure(1, weight=1)

        note = self.project.data.note(self.note_id)
        current = set(note.links or []) if note else set()

        self.targets: List[str] = []
        data = self.project.data
        for chapter in data.ordered_chapters():
            for scene in data.scenes_in(chapter.id):
                self.targets.append(scene.id)
                self.listbox.insert(
                    "end", f"Scene      {scene.display}  ({chapter.display})")
        for entity_type in ("character", "location", "item", "faction",
                            "thread"):
            for entity in data.entities_of(entity_type):
                self.targets.append(entity.id)
                label = ENTITY_LABELS.get(entity_type, entity_type)
                self.listbox.insert("end", f"{label:<10s} {entity.display}")

        for index, target_id in enumerate(self.targets):
            if target_id in current:
                self.listbox.selection_set(index)

    def collect(self) -> Optional[bool]:
        chosen = [self.targets[i] for i in self.listbox.curselection()]
        self.project.set_note_links(self.note_id, chosen)
        self.project.save()
        return True
