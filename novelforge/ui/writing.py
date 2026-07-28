"""
The editor's writing intelligence: completion, the project's own
dictionary, and the live spelling and grammar marks.

Split out of app.py, which had grown past three and a half thousand
lines and was where nearly every defect of the last few days lived - a
missing import hid in it three separate times. These methods are one
coherent feature with one entry point (the editor) and almost no
coupling to the binder or the compiler, so they lift out cleanly.

A mixin rather than a separate object: every one of these is a command
the menus and key bindings already call as `self.cmd_...`, and changing
that at the same time as moving the code would make the move impossible
to review. `App` inherits it; nothing else changed.
"""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Dict, List, Optional, Tuple

from ..config import settings
from . import dialogs


class WritingIntelligence:
    """Mixed into App. Everything here assumes App's attributes."""

    def lexicon(self, rebuild: bool = False):
        """
        The project's own vocabulary, built once and reused.

        Rebuilt when the manuscript changes, which the story graph already
        tracks, so this rides on that rather than re-reading anything.
        """
        from .. import lexicon as lex_module
        from .. import storygraph

        graph = storygraph.cached_graph(self.project)
        # Deliberately NOT keyed on the graph's identity. The graph is rebuilt
        # whenever a scene changes, so that made every typing pause rebuild
        # the whole lexicon from disk - seconds of frozen interface, in the
        # middle of writing. The cast and the accepted words are what the
        # lexicon is actually made of; new prose can wait for the next
        # explicit rebuild.
        signature = (str(self.project.root),
                     len(self.project.data.entities),
                     len(getattr(self.project.data, "accepted_words", [])))
        if rebuild or getattr(self, "_lex_signature", None) != signature:
            self._lex = lex_module.build(self.project, graph)
            self._lex_signature = signature
        return self._lex

    def _word_at_caret(self) -> Tuple[str, str]:
        """
        (what is being typed, where it starts) in the editor.

        Worked out from the text of the line rather than Tk's "wordstart",
        which does not agree with what a novelist means by a word - it stops
        at apostrophes and does not reach back over "King Ro" to offer a name.
        """
        try:
            line = self.editor.text.get("insert linestart", "insert")
        except tk.TclError:
            return "", ""
        if not line or not line[-1].isalpha():
            return "", ""
        # Reach back over a capitalised run so "King Ro" completes as a name,
        # falling back to the single word being typed.
        match = re.search(r"(?:[A-Z][A-Za-z'\-]*\s+){1,3}[A-Za-z'\-]+$", line)
        if not match:
            match = re.search(r"[A-Za-z'\-]+$", line)
        if not match:
            return "", ""
        prefix = match.group(0)
        return prefix, self.editor.text.index(f"insert -{len(prefix)}c")

    def cmd_complete(self, event=None):
        """Suggest a continuation from this book's own vocabulary."""
        if not self.project or not self.current_scene_id:
            return "break"
        prefix, start = self._word_at_caret()
        lex = self.lexicon()
        options = lex.complete(prefix) if prefix else []
        if not options:
            before = self.editor.text.get("insert linestart", "insert")
            options = lex.next_words(before)
            start = self.editor.text.index("insert")
            prefix = ""
        if not options:
            self.status.say(
                "Nothing to suggest yet - the book has not used a word like "
                "that.", 5)
            return "break"
        self._show_completions(options, prefix, start)
        return "break"

    def _show_completions(self, options, prefix: str, start: str) -> None:
        self._close_completions()
        self.editor.text.update_idletasks()
        try:
            box = self.editor.text.bbox("insert")
        except tk.TclError:
            box = None
        # bbox is None when the caret is not currently drawn. Falling back to
        # the top-left of the editor is far better than silently doing
        # nothing, which is what a writer would read as "the key is broken".
        x, y, height = (box[0], box[1], box[3]) if box else (8, 8, 16)
        popup = tk.Toplevel(self)
        popup.wm_overrideredirect(True)
        popup.attributes("-topmost", True)
        listbox = tk.Listbox(popup, height=min(8, len(options)),
                             activestyle="none", exportselection=False,
                             width=max(14, max(len(o) for o in options) + 2))
        listbox.grid(row=0, column=0)
        for option in options:
            listbox.insert("end", option)
        listbox.selection_set(0)
        popup.geometry(
            f"+{self.editor.text.winfo_rootx() + x}"
            f"+{self.editor.text.winfo_rooty() + y + height + 2}")
        self._completion = (popup, listbox, prefix, start)

        def accept(_event=None):
            selection = listbox.curselection()
            if selection:
                self._apply_completion(options[selection[0]], prefix, start)
            self._close_completions()
            return "break"

        def move(step):
            def handler(_event=None):
                current = listbox.curselection()
                index = (current[0] if current else 0) + step
                index = max(0, min(index, len(options) - 1))
                listbox.selection_clear(0, "end")
                listbox.selection_set(index)
                listbox.see(index)
                return "break"
            return handler

        # Bindings added to the editor must be removed again when the popup
        # closes. Adding them with add="+" and never unbinding left a handler
        # referencing a destroyed listbox, so every later Enter, Tab or arrow
        # key in the editor raised a TclError - the popup broke typing itself.
        self._completion_bindings = []
        for sequence, handler in (("<Return>", accept), ("<Tab>", accept),
                                  ("<Down>", move(1)), ("<Up>", move(-1)),
                                  ("<Escape>",
                                   lambda _e: self._close_completions())):
            listbox.bind(sequence, handler)
            token = self.editor.text.bind(sequence, handler, add="+")
            self._completion_bindings.append((sequence, token))
        listbox.bind("<Double-Button-1>", accept)

    def _apply_completion(self, chosen: str, prefix: str, start: str) -> None:
        self.editor.text.edit_separator()
        if prefix:
            self.editor.text.delete(start, "insert")
        elif not self.editor.text.get("insert -1c", "insert").isspace():
            self.editor.text.insert("insert", " ")
        self.editor.text.insert("insert", chosen)
        self.editor.text.edit_separator()
        self._editor_dirty = True

    def _close_completions(self, _event=None) -> None:
        # Unbind first: a handler left on the editor would still be holding a
        # reference to the listbox that is about to be destroyed.
        for sequence, token in getattr(self, "_completion_bindings", []):
            try:
                self.editor.text.unbind(sequence, token)
            except tk.TclError:
                pass
        self._completion_bindings = []
        state = getattr(self, "_completion", None)
        if not state:
            return
        try:
            state[0].destroy()
        except tk.TclError:
            pass
        self._completion = None

    def _schedule_writing_check(self) -> None:
        """Re-check the scene shortly after typing stops."""
        if self.editor_check:
            self.editor_check.schedule()

    def _run_writing_check(self) -> None:
        """Check now, rather than waiting for the idle timer."""
        if self.editor_check:
            self.editor_check.refresh()

    def _on_check_summary(self, counts: Dict[str, int]) -> None:
        """Say what was found, so it is obvious the check is running at all."""
        if counts:
            self.status.say(
                "  ".join(f"{kind}: {n}" for kind, n in sorted(counts.items()))
                + "    (right-click a mark to fix it)", 0)
        else:
            self.status.say("")

    @property
    def _writing_hits(self):
        return self.editor_check.hits if self.editor_check else []

    def _hit_at(self, index: str):
        """The finding under a text index, if any."""
        return self.editor_check.hit_at(index) if self.editor_check else None

    def _apply_fix(self, hit) -> None:
        if not self.editor_check:
            return
        self.editor_check.apply(hit)
        self._editor_dirty = True

    def cmd_writing_check(self) -> None:
        """The full list for this scene, in one window."""
        if not self.require_project() or not self.current_scene_id:
            messagebox.showinfo("Open a scene",
                                "Select a scene to check.", parent=self)
            return
        from .. import grammar

        text = self.editor.get_value()
        hits = grammar.check(text, self.lexicon(), limit=300)
        scene = self.project.data.scene(self.current_scene_id)
        body = grammar.report(hits, text,
                              f"WRITING CHECK - {scene.title if scene else ''}")
        window = dialogs.ReportWindow(self, "Writing check", body,
                                      width=760, height=640)
        if hits:
            window.add_action("Fix everything obvious",
                              lambda: self._fix_all_obvious(hits, window))

    def _fix_all_obvious(self, hits, window) -> None:
        """
        Apply only the corrections that are not judgement calls.

        Spelling and missing apostrophes have exactly one right answer.
        Agreement and usage often do not - "he were" may be deliberate - so
        those are left for the writer.
        """
        safe = [h for h in hits
                if h.suggestion and h.kind in ("spelling", "typing")]
        if not safe:
            messagebox.showinfo(
                "Nothing automatic",
                "The remaining findings need a decision only you can make.",
                parent=window)
            return
        widget = self.editor.text
        widget.edit_separator()
        for hit in sorted(safe, key=lambda h: -h.start):
            widget.delete(f"1.0 + {hit.start}c", f"1.0 + {hit.end}c")
            widget.insert(f"1.0 + {hit.start}c", hit.suggestion)
        widget.edit_separator()
        self._editor_dirty = True
        self.save_editor(snapshot=False)
        self._schedule_writing_check()
        window.destroy()
        self.status.say(f"Fixed {len(safe)} spellings. Ctrl+Z undoes it.", 8)

    def cmd_toggle_live_check(self) -> None:
        settings["live_writing_check"] = bool(self.live_check_var.get())
        if not self.editor_check:
            return
        if settings["live_writing_check"]:
            self.editor_check.refresh()
            self.status.say("Underlining mistakes as you type.", 5)
        else:
            self.editor_check.clear()
            self.status.say("Live checking off. Shift+F7 still checks on "
                            "demand.", 6)
        # The inspector's fields have their own checkers; rebuilding the
        # panel is the cheapest way to bring them into line.
        self.render_selection()

    def cmd_lexicon_report(self) -> None:
        if not self.require_project():
            return
        from .. import lexicon as lex_module

        body = lex_module.report(self.project, self.lexicon(rebuild=True))
        dialogs.ReportWindow(self, "What the editor knows", body)

    def cmd_check_names(self) -> None:
        """Names in this scene that look like a known one typed wrong."""
        if not self.require_project() or not self.current_scene_id:
            messagebox.showinfo("Open a scene",
                                "Select a scene to check.", parent=self)
            return
        lex = self.lexicon()
        found = lex.suspicious(self.editor.get_value())
        if not found:
            self.status.say("Every name in this scene matches the book.", 6)
            return
        lines = ["NAMES THAT MAY BE TYPED WRONG", "=" * 56, "",
                 "Each of these is capitalised, is not a name the book knows,",
                 "and is close to one that is.", ""]
        for phrase, close in found:
            lines.append(f"  {phrase}")
            lines.append(f"      did you mean:  {', '.join(close)}")
            lines.append("")
        dialogs.ReportWindow(self, "Check names in this scene",
                             "\n".join(lines), width=640, height=520)

    def on_editor_right_click(self, event) -> None:
        """A right-click menu that knows the novel."""
        if not self.project:
            return
        text = self.editor.text
        try:
            text.mark_set("insert", f"@{event.x},{event.y}")
        except tk.TclError:
            return
        word = text.get("insert wordstart", "insert wordend").strip()
        menu = tk.Menu(self, tearoff=0)

        # A finding under the caret comes first: that is what the writer
        # right-clicked the underline for.
        hit = self._hit_at("insert")
        if hit is not None:
            menu.add_command(label=hit.message, state="disabled")
            if hit.suggestion:
                menu.add_command(
                    label=f"Change to  '{' '.join(hit.suggestion.split())}'",
                    command=lambda h=hit: self._apply_fix(h))
            if hit.kind in ("spelling", "name"):
                menu.add_command(
                    label=f"Keep '{hit.text}' - add to the dictionary",
                    command=lambda w=hit.text: self.cmd_accept_word(w))
            menu.add_separator()

        menu.add_command(label="Cut",
                         command=lambda: text.event_generate("<<Cut>>"))
        menu.add_command(label="Copy",
                         command=lambda: text.event_generate("<<Copy>>"))
        menu.add_command(label="Paste",
                         command=lambda: text.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Suggest a word here  (Ctrl+Space)",
                         command=self.cmd_complete)

        if word:
            lex = self.lexicon()
            term = lex.term(word)
            close = lex.near_miss(word)
            if close:
                for suggestion in close:
                    menu.add_command(
                        label=f"Change to '{suggestion}'",
                        command=lambda s=suggestion: self._replace_word(s))
            if term and term.entity_id:
                menu.add_separator()
                menu.add_command(
                    label=f"Open the sheet for '{term.text}'",
                    command=lambda e=term.entity_id: self._open_entity(e))
                menu.add_command(
                    label=f"Where is '{term.text}' mentioned?",
                    command=lambda e=term.entity_id: self._mentions_of(e))
            menu.add_separator()
            menu.add_command(label=f"Rename '{word}' everywhere...",
                             command=lambda: self._rename_everywhere(word))
            if not lex.knows(word):
                menu.add_command(
                    label=f"Add '{word}' to the dictionary",
                    command=lambda: self.cmd_accept_word(word))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _replace_word(self, replacement: str) -> None:
        text = self.editor.text
        text.edit_separator()
        text.delete("insert wordstart", "insert wordend")
        text.insert("insert", replacement)
        text.edit_separator()
        self._editor_dirty = True

    def _open_entity(self, entity_id: str) -> None:
        self.save_editor(snapshot=False)
        self.tree.selection_set(f"entity:{entity_id}")
        self.tree.see(f"entity:{entity_id}")
        self.render_selection()

    def _mentions_of(self, entity_id: str) -> None:
        self.selection_kind, self.selection_id = "entity", entity_id
        self.cmd_mentions()

    def _rename_everywhere(self, word: str) -> None:
        self.save_editor(snapshot=False)
        from .storyviews import ReplaceWindow

        window = ReplaceWindow(self, self.project, self.refresh_tree)
        window.find_entry.insert(0, word)
        window.replace_entry.focus_set()

    def cmd_accept_word(self, word: str = "") -> None:
        """Teach the editor a word it has never seen."""
        if not self.require_project():
            return
        if not word:
            word = self.editor.text.get("insert wordstart",
                                        "insert wordend").strip()
        if not word:
            return
        accepted = self.project.data.accepted_words
        if word.lower() in {w.lower() for w in accepted}:
            self.status.say(f"'{word}' is already in the dictionary.", 4)
            return
        with self.project.action(f"accept the word '{word}'"):
            accepted.append(word)
            self.project.mark_dirty()
        self.project.save()
        self.lexicon(rebuild=True)
        self._sync_history_menu()
        self.status.say(f"'{word}' added. It will not be questioned again.", 6)
