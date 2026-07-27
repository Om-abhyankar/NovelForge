"""
The story knowledge graph, and everything that falls out of it.

Every other module here treats the novel as a *list* - scenes in order, entities
in a sidebar. This one treats it as a *network*: who appears where, which scene
introduces what, which thread is still open, what breaks if you delete Chapter 8.
Most of the genuinely hard questions a novelist asks are graph questions, and
they are unanswerable from a flat list.

Why one module rather than five: the continuity checker, the dependency map, the
story bible and the question answerer all need the same expensive thing - a full
read of the manuscript with every entity located in it. Building that once and
sharing it is the difference between "instant" and "unusable on a real novel".

    graph = build(project)              # reads every scene once
    issues = check_continuity(project, graph)
    report = dependencies(project, graph, scene_id)
    path   = write_story_bible(project, graph)
    text   = answer(project, graph, "where does Ada first appear?")

Performance note. The obvious implementation is `for entity: for scene: search`,
which is what `Project.find_mentions` does for a single entity. Done for every
entity that is O(entities x scenes) file reads - on a 60-scene novel with 40
characters that is 2,400 document opens and takes minutes. Here each scene is
read exactly once and matched against a single combined pattern built from every
name and alias in the project, so the cost is O(scenes) reads regardless of how
large the cast grows.

Nothing in this module contacts a network, and nothing needs to. Every answer is
derived from your own files.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from . import docxio
from .model import ENTITY_LABELS, ENTITY_PLURAL

# --------------------------------------------------------------------------
# Graph primitives
# --------------------------------------------------------------------------

#: Edge kinds, weakest to strongest claim of "this really is in the scene".
#: `mentions` is inferred from the prose; the others are declared by the writer.
EDGE_KINDS = ("in_chapter", "pov", "linked", "mentions", "about", "at",
              "covers", "references")


@dataclass
class Node:
    """One thing in the story. `ref` is the underlying model object."""

    id: str
    kind: str                   # scene | chapter | character | location | ...
    name: str
    order: int = 0              # reading position, for scenes
    ref: Any = None

    @property
    def label(self) -> str:
        return ENTITY_LABELS.get(self.kind, self.kind.title())


@dataclass
class Edge:
    source: str
    target: str
    kind: str
    weight: int = 1
    #: False when the link was detected in the prose rather than declared in the
    #: manifest. The distinction matters: a detected-but-not-declared link is a
    #: continuity finding, not an error.
    explicit: bool = True


@dataclass
class StoryGraph:
    nodes: Dict[str, Node] = field(default_factory=dict)
    edges: List[Edge] = field(default_factory=list)

    #: scene id -> prose, read once at build time and reused by every consumer.
    scene_text: Dict[str, str] = field(default_factory=dict)
    #: scene id -> reading position (0-based).
    scene_order: Dict[str, int] = field(default_factory=dict)
    #: scene ids in reading order.
    reading_order: List[str] = field(default_factory=list)
    #: lowercase name -> entity ids that answer to it. More than one id means
    #: the name is ambiguous, which is itself worth reporting.
    name_lookup: Dict[str, List[str]] = field(default_factory=dict)

    # -- construction helpers -------------------------------------------
    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node

    def add_edge(self, source: str, target: str, kind: str,
                 weight: int = 1, explicit: bool = True) -> None:
        # Both ends must exist, or the graph grows phantom nodes from stale
        # manifest ids. Dangling ids are reported by the continuity checker
        # instead, where the writer can actually see them.
        if source not in self.nodes or target not in self.nodes:
            return
        self.edges.append(Edge(source, target, kind, weight, explicit))

    # -- queries ---------------------------------------------------------
    def out_edges(self, node_id: str, kinds: Sequence[str] = ()) -> List[Edge]:
        return [e for e in self.edges
                if e.source == node_id and (not kinds or e.kind in kinds)]

    def in_edges(self, node_id: str, kinds: Sequence[str] = ()) -> List[Edge]:
        return [e for e in self.edges
                if e.target == node_id and (not kinds or e.kind in kinds)]

    def neighbours(self, node_id: str) -> List[Node]:
        seen: Dict[str, Node] = {}
        for edge in self.edges:
            other = None
            if edge.source == node_id:
                other = edge.target
            elif edge.target == node_id:
                other = edge.source
            if other and other in self.nodes:
                seen[other] = self.nodes[other]
        return list(seen.values())

    def nodes_of(self, kind: str) -> List[Node]:
        return [n for n in self.nodes.values() if n.kind == kind]

    def scenes_with(self, entity_id: str,
                    include_mentions: bool = True) -> List[str]:
        """Scene ids featuring an entity, in reading order."""
        kinds = ("linked", "pov") + (("mentions",) if include_mentions else ())
        found = {e.source for e in self.in_edges(entity_id, kinds)}
        return [s for s in self.reading_order if s in found]

    def appearances(self, entity_id: str) -> int:
        return len(self.scenes_with(entity_id))

    def first_appearance(self, entity_id: str) -> Optional[str]:
        scenes = self.scenes_with(entity_id)
        return scenes[0] if scenes else None

    def last_appearance(self, entity_id: str) -> Optional[str]:
        scenes = self.scenes_with(entity_id)
        return scenes[-1] if scenes else None

    def position(self, scene_id: str) -> float:
        """Where a scene sits in the book, 0.0 to 1.0."""
        if not self.reading_order:
            return 0.0
        return self.scene_order.get(scene_id, 0) / max(1, len(self.reading_order) - 1)

    def co_occurring(self, entity_id: str) -> Counter:
        """
        Entities sharing scenes with this one, counted by shared scenes.

        Deduplicated per scene: a character reached by a declared link, a POV
        assignment and a name in the prose is present once, not three times.
        """
        shared: Counter = Counter()
        for scene_id in self.scenes_with(entity_id):
            here = {e.target for e in
                    self.out_edges(scene_id, ("linked", "pov", "mentions"))}
            for other in here:
                if other != entity_id:
                    shared[other] += 1
        return shared


# --------------------------------------------------------------------------
# Building
# --------------------------------------------------------------------------


def _build_name_lookup(entities) -> Dict[str, List[str]]:
    lookup: Dict[str, List[str]] = defaultdict(list)
    for entity in entities:
        for name in entity.all_names():
            key = name.lower()
            if entity.id not in lookup[key]:
                lookup[key].append(entity.id)
    return dict(lookup)


def _mention_pattern(lookup: Dict[str, List[str]]) -> Optional[re.Pattern]:
    """
    One alternation covering every name in the project.

    Sorted longest-first so "Ada Vane" is consumed as one match rather than
    matching "Ada" and leaving "Vane" to match separately - otherwise a single
    mention of a full name counts as two.
    """
    if not lookup:
        return None
    names = sorted(lookup, key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(n) for n in names) + r")\b",
                      re.IGNORECASE)


#: Last graph built, keyed by project root. Reading a hundred scene documents
#: takes seconds; almost every use of the graph happens when nothing has
#: changed since the last one, so the honest fix is not to rebuild.
_CACHE: Dict[str, Tuple[Tuple, StoryGraph]] = {}


def _signature(project) -> Tuple:
    """
    Everything a graph depends on, cheaply.

    File modification times rather than contents: a stat call per scene is
    about a thousand times faster than opening the document, and any edit
    through this tool or through Word moves the mtime.
    """
    data = project.data
    scenes = []
    for scene in data.scenes:
        mtime = 0.0
        if scene.docx:
            try:
                mtime = project.abs(scene.docx).stat().st_mtime
            except OSError:
                mtime = -1.0
        scenes.append((scene.id, scene.chapter_id, scene.order, scene.title,
                       scene.pov_id, mtime,
                       tuple(scene.character_ids), tuple(scene.location_ids),
                       tuple(scene.item_ids), tuple(scene.faction_ids),
                       tuple(scene.thread_ids)))
    entities = [(e.id, e.type, e.name, tuple(e.aliases)) for e in data.entities]
    notes = [(n.id, n.title, tuple(getattr(n, "links", []) or []))
             for n in data.notes]
    events = [(e.id, e.title, e.scene_id, e.story_date, e.kind,
               tuple(e.character_ids), e.location_id) for e in data.events]
    beats = [(b.key, b.name, tuple(b.scene_ids)) for b in data.beats]
    chapters = [(c.id, c.title, c.order) for c in data.chapters]
    from . import mapstory

    return (tuple(scenes), tuple(entities), tuple(notes), tuple(events),
            tuple(beats), tuple(chapters), mapstory.map_signature(project))


def invalidate(project=None) -> None:
    """Drop the cached graph. Called when a project is closed or reloaded."""
    if project is None:
        _CACHE.clear()
    else:
        _CACHE.pop(str(project.root), None)


def cached_graph(project) -> Optional["StoryGraph"]:
    """
    The current graph if one is already built and still valid, else None.

    For callers that want to be helpful when the information is to hand but
    must not stall the interface to get it. Building from cold means reading
    every scene document - about twenty-five seconds on a 300,000 word novel -
    and no confirmation dialog is worth that wait.
    """
    cached = _CACHE.get(str(project.root))
    if cached and cached[0] == _signature(project):
        return cached[1]
    return None


def build(project, read_prose: bool = True, use_cache: bool = True,
          progress: Optional[Any] = None) -> StoryGraph:
    """
    Assemble the graph. `read_prose=False` skips document reads, which gives a
    manifest-only graph - fast, and enough for structural questions.

    Repeated calls with nothing changed return the previous graph, so opening
    four graph-backed windows in a row costs one manuscript read, not four.

    `progress(done, total)` is called as the scenes are read. On a 300,000
    word novel the first build takes around twenty-five seconds, essentially
    all of it opening documents, and an interface that simply stops for that
    long looks broken.
    """
    if use_cache and read_prose:
        signature = _signature(project)
        cached = _CACHE.get(str(project.root))
        if cached and cached[0] == signature:
            return cached[1]
    else:
        signature = None

    data = project.data
    graph = StoryGraph()

    for chapter in data.ordered_chapters():
        graph.add_node(Node(chapter.id, "chapter", chapter.display, chapter.order,
                            chapter))

    ordered = data.ordered_scenes()
    for index, scene in enumerate(ordered):
        graph.add_node(Node(scene.id, "scene", scene.display, index, scene))
        graph.scene_order[scene.id] = index
        graph.reading_order.append(scene.id)

    for entity in data.entities:
        graph.add_node(Node(entity.id, entity.type, entity.display, entity.order,
                            entity))

    for event in project.ordered_events():
        graph.add_node(Node(event.id, "event", event.title or "(untitled event)",
                            event.order, event))

    for note in data.notes:
        graph.add_node(Node(note.id, "note", note.title or "(untitled note)",
                            note.order, note))

    for beat in data.beats:
        graph.add_node(Node(f"beat:{beat.key}", "beat", beat.name, beat.order,
                            beat))

    # -- declared edges --------------------------------------------------
    for scene in ordered:
        graph.add_edge(scene.id, scene.chapter_id, "in_chapter")
        if scene.pov_id:
            graph.add_edge(scene.id, scene.pov_id, "pov")
        for group in (scene.character_ids, scene.location_ids, scene.item_ids,
                      scene.faction_ids, scene.thread_ids):
            for entity_id in group:
                graph.add_edge(scene.id, entity_id, "linked")

    for event in data.events:
        if event.scene_id:
            graph.add_edge(event.id, event.scene_id, "covers")
        for cid in event.character_ids:
            graph.add_edge(event.id, cid, "about")
        if event.location_id:
            graph.add_edge(event.id, event.location_id, "at")

    for beat in data.beats:
        for scene_id in beat.scene_ids:
            graph.add_edge(f"beat:{beat.key}", scene_id, "covers")

    # Research notes linked to story elements. `links` is newer than the rest
    # of the manifest, so read it defensively.
    for note in data.notes:
        for target in getattr(note, "links", []) or []:
            graph.add_edge(note.id, target, "references")

    # Maps join the graph as nodes, so the dependency map, the story bible and
    # the question box all see them without knowing maps exist.
    from . import mapstory

    try:
        mapstory.attach(project, graph)
    except Exception:
        pass        # a damaged map must not stop the graph being built

    # -- detected edges --------------------------------------------------
    graph.name_lookup = _build_name_lookup(data.entities)
    if read_prose:
        pattern = _mention_pattern(graph.name_lookup)
        total = len(ordered)
        for index, scene in enumerate(ordered):
            if progress is not None and (index % 5 == 0 or index == total - 1):
                try:
                    progress(index + 1, total)
                except Exception:
                    progress = None       # a failing reporter must not stop it
            text = ""
            if scene.docx:
                try:
                    text = docxio.read_prose(project.abs(scene.docx))
                except Exception:
                    # An unreadable scene must not abort the whole graph; it
                    # simply contributes nothing.
                    text = ""
            graph.scene_text[scene.id] = text
            if not text or pattern is None:
                continue
            counts: Counter = Counter()
            for match in pattern.finditer(text):
                for entity_id in graph.name_lookup.get(match.group(1).lower(), []):
                    counts[entity_id] += 1
            for entity_id, count in counts.items():
                graph.add_edge(scene.id, entity_id, "mentions", count,
                               explicit=False)

    if signature is not None:
        _CACHE[str(project.root)] = (signature, graph)
    return graph


# --------------------------------------------------------------------------
# Continuity checking
# --------------------------------------------------------------------------


@dataclass
class Issue:
    severity: str               # high | medium | low
    category: str
    title: str
    detail: str
    where: str = ""

    @property
    def rank(self) -> int:
        return {"high": 0, "medium": 1, "low": 2}.get(self.severity, 3)


def _date_key(value: str, fallback: float) -> float:
    from .project import _date_sort_key

    return _date_sort_key(value, fallback)


def _declared_ids(scene) -> Set[str]:
    return set(scene.character_ids + scene.location_ids + scene.item_ids
               + scene.faction_ids + scene.thread_ids
               + ([scene.pov_id] if scene.pov_id else []))


def check_continuity(project, graph: StoryGraph) -> List[Issue]:
    """
    Every check that can be made honestly offline.

    These are deliberately conservative. A continuity checker that cries wolf
    gets switched off, so anything ambiguous is reported at 'low' and phrased
    as a question rather than an accusation.
    """
    data = project.data
    issues: List[Issue] = []
    scenes = data.ordered_scenes()
    known_ids = {e.id for e in data.entities}
    total = len(scenes)

    def name_of(entity_id: str) -> str:
        entity = data.entity(entity_id)
        return entity.name if entity else "(deleted)"

    # 1. Links pointing at entities that no longer exist ------------------
    for scene in scenes:
        for entity_id in _declared_ids(scene):
            if entity_id not in known_ids:
                issues.append(Issue(
                    "high", "Broken link",
                    f"'{scene.display}' links to something deleted",
                    "The scene still references an entity that is no longer in "
                    "the project. Open the scene and clear the stale link.",
                    scene.display,
                ))

    # 2. Characters in the prose but not linked to the scene --------------
    for scene in scenes:
        declared = _declared_ids(scene)
        for edge in graph.out_edges(scene.id, ("mentions",)):
            if edge.target in declared:
                continue
            node = graph.nodes.get(edge.target)
            if not node or node.kind not in ("character", "location", "item",
                                             "faction"):
                continue
            # A named character in a scene is worth linking even once - that is
            # usually someone speaking. A place or object named in passing is
            # much more often scenery, so those need a second mention before
            # they are worth interrupting the writer for.
            if edge.weight < (1 if node.kind == "character" else 2):
                continue
            issues.append(Issue(
                "low", "Missing link",
                f"'{node.name}' appears in '{scene.display}' but is not linked",
                f"The name occurs {edge.weight} "
                f"{'time' if edge.weight == 1 else 'times'} in the prose. "
                f"Linking it keeps the story bible, the relationship web and "
                f"the dependency map accurate.",
                scene.display,
            ))

    # 3. Linked but never named in the prose ------------------------------
    for scene in scenes:
        if not graph.scene_text.get(scene.id):
            continue            # unwritten scene: linking ahead is normal
        mentioned = {e.target for e in graph.out_edges(scene.id, ("mentions",))}
        for entity_id in _declared_ids(scene):
            if entity_id in mentioned or entity_id not in known_ids:
                continue
            entity = data.entity(entity_id)
            if entity and entity.type == "thread":
                continue        # threads are abstractions, rarely named on page
            issues.append(Issue(
                "low", "Unused link",
                f"'{name_of(entity_id)}' is linked to '{scene.display}' but "
                f"never named in it",
                "Either the link is left over from an earlier draft, or the "
                "character is present but unnamed - both are fine, this is "
                "only worth a glance.",
                scene.display,
            ))

    # 4. POV character absent from their own scene ------------------------
    for scene in scenes:
        if not scene.pov_id or not graph.scene_text.get(scene.id):
            continue
        mentioned = {e.target for e in graph.out_edges(scene.id, ("mentions",))}
        if scene.pov_id not in mentioned:
            issues.append(Issue(
                "medium", "Point of view",
                f"The POV character of '{scene.display}' is never named in it",
                f"'{name_of(scene.pov_id)}' carries the viewpoint but does not "
                f"appear by name. In deep third that can be deliberate; in most "
                f"other modes it means the POV is set wrong.",
                scene.display,
            ))

    # 5. Story dates running backwards ------------------------------------
    dated = [s for s in scenes if s.story_date.strip()]
    for previous, current in zip(dated, dated[1:]):
        before = _date_key(previous.story_date, 0)
        after = _date_key(current.story_date, 0)
        if after < before:
            issues.append(Issue(
                "medium", "Chronology",
                f"'{current.display}' is dated before the scene that precedes it",
                f"'{previous.display}' is {previous.story_date} and "
                f"'{current.display}' is {current.story_date}. That is fine for "
                f"a deliberate flashback, and a mistake otherwise.",
                current.display,
            ))

    # 6. Events disagreeing with the scene they are pinned to -------------
    for event in data.events:
        if not event.scene_id or not event.story_date.strip():
            continue
        scene = data.scene(event.scene_id)
        if not scene or not scene.story_date.strip():
            continue
        if abs(_date_key(event.story_date, 0)
               - _date_key(scene.story_date, 0)) > 0.5:
            issues.append(Issue(
                "medium", "Chronology",
                f"Event '{event.title}' and its scene disagree on the date",
                f"The event says {event.story_date}; '{scene.display}' says "
                f"{scene.story_date}.",
                event.title,
            ))

    # 7. Characters appearing outside their own lifetime ------------------
    births = {e.character_ids[0]: e for e in data.events
              if e.kind == "birth" and e.character_ids and e.story_date.strip()}
    deaths = {e.character_ids[0]: e for e in data.events
              if e.kind == "death" and e.character_ids and e.story_date.strip()}
    for entity_id, death in deaths.items():
        limit = _date_key(death.story_date, 0)
        for scene_id in graph.scenes_with(entity_id):
            scene = data.scene(scene_id)
            if not scene or not scene.story_date.strip():
                continue
            if _date_key(scene.story_date, 0) > limit:
                issues.append(Issue(
                    "high", "Lifespan",
                    f"'{name_of(entity_id)}' appears after their death",
                    f"Death is recorded as {death.story_date}, but "
                    f"'{scene.display}' is dated {scene.story_date}. If this is "
                    f"a flashback or a ghost, ignore this.",
                    scene.display,
                ))
    for entity_id, birth in births.items():
        start = _date_key(birth.story_date, 0)
        for scene_id in graph.scenes_with(entity_id):
            scene = data.scene(scene_id)
            if not scene or not scene.story_date.strip():
                continue
            if _date_key(scene.story_date, 0) < start:
                issues.append(Issue(
                    "high", "Lifespan",
                    f"'{name_of(entity_id)}' appears before they were born",
                    f"Birth is recorded as {birth.story_date}, but "
                    f"'{scene.display}' is dated {scene.story_date}.",
                    scene.display,
                ))

    # 8. Plot threads that stop without resolving -------------------------
    if total >= 6:
        for thread in data.entities_of("thread"):
            appearances = graph.scenes_with(thread.id)
            if not appearances:
                continue
            last = graph.position(appearances[-1])
            if last < 0.75 and len(appearances) >= 2:
                issues.append(Issue(
                    "medium", "Open thread",
                    f"Plot thread '{thread.name}' stops {int(last * 100)}% in",
                    f"It runs through {len(appearances)} scenes and then "
                    f"disappears before the last quarter of the book. Threads "
                    f"that vanish rather than resolve are the single most "
                    f"common note from readers.",
                    thread.name,
                ))

    # 9. Entities with a sheet and no appearances -------------------------
    for entity in data.entities:
        if entity.type == "thread":
            continue
        if not graph.scenes_with(entity.id):
            issues.append(Issue(
                "low", "Unused",
                f"{ENTITY_LABELS.get(entity.type, entity.type)} "
                f"'{entity.name}' never appears",
                "It has a sheet but occurs in no scene, by link or by name. "
                "Either it is still to be written, or it is a leftover.",
                entity.name,
            ))

    # 10. Items introduced and forgotten ----------------------------------
    for item in data.entities_of("item"):
        appearances = graph.scenes_with(item.id)
        if len(appearances) == 1 and total >= 8:
            scene = data.scene(appearances[0])
            issues.append(Issue(
                "low", "Chekhov",
                f"Item '{item.name}' appears exactly once",
                f"It shows up in '{scene.display if scene else '?'}' and never "
                f"again. An object important enough to have a sheet usually "
                f"wants a second appearance.",
                item.name,
            ))

    # 11. Names a reader will confuse -------------------------------------
    # Reported once per pair, not once per shared word: "Iron Keep" and "Iron
    # Keep Ruins" share both "iron" and "keep" and would otherwise be raised
    # twice. Nested names are skipped entirely - one being contained in the
    # other is how a place and its ruin are *supposed* to read.
    reported_pairs: Set[Tuple[str, str]] = set()
    for name, ids in graph.name_lookup.items():
        if len(ids) < 2:
            continue
        for index, first in enumerate(ids):
            for second in ids[index + 1:]:
                pair = tuple(sorted((first, second)))
                if pair in reported_pairs:
                    continue
                one, two = name_of(first).lower(), name_of(second).lower()
                if one in two or two in one:
                    continue
                reported_pairs.add(pair)
                issues.append(Issue(
                    "medium", "Confusable names",
                    f"'{name_of(first)}' and '{name_of(second)}' share the "
                    f"name '{name}'",
                    "Readers mix these up, and so does every tool that scans "
                    "your prose - including this one, which cannot tell which "
                    "of them a bare '" + name + "' means.",
                    name,
                ))

    # 12. Bracket tags left in the manuscript -----------------------------
    # Scanned from the text the graph already holds. Project.collect_bracket_tags
    # re-opens every scene document, which on a 500-scene novel costs about
    # eight seconds - for text that was read moments ago.
    from .project import BRACKET_TAG

    found = 0
    for scene_id in graph.reading_order:
        if found >= 40:
            break
        text = graph.scene_text.get(scene_id, "")
        if not text or "[" not in text:
            continue
        node = graph.nodes.get(scene_id)
        for match in BRACKET_TAG.finditer(text):
            issues.append(Issue(
                "medium", "Unfinished",
                f"Open tag in '{node.name if node else '?'}'",
                match.group(1).strip()[:200],
                node.name if node else "",
            ))
            found += 1
            if found >= 40:
                break

    # 13. Beats with nothing written against them -------------------------
    for beat in data.beats:
        if beat.scene_ids or not beat.answer.strip():
            continue
        issues.append(Issue(
            "low", "Structure",
            f"Beat '{beat.name}' has no scene",
            "It is planned but nothing in the manuscript is attached to it.",
            beat.name,
        ))

    # 14. Scenes where nothing changes ------------------------------------
    for scene in scenes:
        start, end = scene.value_start.strip(), scene.value_end.strip()
        if start and end and start.lower() == end.lower():
            issues.append(Issue(
                "low", "Flat scene",
                f"'{scene.display}' starts and ends on the same value",
                f"Both are '{start}'. A scene where the charge does not change "
                f"is an episode, not a scene.",
                scene.display,
            ))

    # 15. Major characters who arrive too late ----------------------------
    if total >= 10:
        for character in data.entities_of("character"):
            if character.role in ("Walk-on", "Supporting", ""):
                continue
            first = graph.first_appearance(character.id)
            if first and graph.position(first) > 0.6:
                scene = data.scene(first)
                issues.append(Issue(
                    "medium", "Late arrival",
                    f"{character.role} '{character.name}' first appears "
                    f"{int(graph.position(first) * 100)}% in",
                    f"Their first scene is '{scene.display if scene else '?'}'. "
                    f"A character with this role usually needs earlier setup or "
                    f"the reader feels ambushed.",
                    character.name,
                ))

    # 16. What only the map can tell us -----------------------------------
    try:
        from . import mapstory

        issues.extend(mapstory.check_maps(project, graph))
    except Exception:
        pass

    issues.sort(key=lambda i: (i.rank, i.category, i.title))
    return issues


def continuity_text(project, issues: Sequence[Issue]) -> str:
    counts = Counter(i.severity for i in issues)
    lines = [
        "CONTINUITY CHECK",
        "=" * 60,
        project.data.title,
        "",
        f"{counts.get('high', 0)} serious   "
        f"{counts.get('medium', 0)} worth a look   "
        f"{counts.get('low', 0)} minor",
        "",
        "Everything here was worked out from your own files. Nothing was sent",
        "anywhere, and none of it is a rule you have to obey - a deliberate",
        "flashback trips half of these checks.",
        "",
    ]
    if not issues:
        lines += ["-" * 60, "",
                  "Nothing to report. Every link resolves, the chronology is",
                  "consistent and no thread is left hanging.", ""]
        return "\n".join(lines)

    current = ""
    for issue in issues:
        if issue.severity != current:
            current = issue.severity
            heading = {"high": "SERIOUS", "medium": "WORTH A LOOK",
                       "low": "MINOR"}[current]
            lines += ["", "-" * 60, heading, "-" * 60, ""]
        lines.append(f"  [{issue.category}] {issue.title}")
        for chunk in _wrap(issue.detail, 66):
            lines.append(f"      {chunk}")
        lines.append("")
    return "\n".join(lines)


def _wrap(text: str, width: int) -> List[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return lines or [""]


# --------------------------------------------------------------------------
# Scene dependency map
# --------------------------------------------------------------------------


@dataclass
class Dependency:
    """What a scene owes, and what is owed to it."""

    scene_id: str
    introduces: List[str] = field(default_factory=list)     # entity ids
    dependents: List[Tuple[str, List[str]]] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    beats: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    only_appearance: List[str] = field(default_factory=list)

    @property
    def risk(self) -> str:
        if self.only_appearance or len(self.dependents) >= 3:
            return "high"
        if self.dependents or self.events or self.beats:
            return "medium"
        return "low"


def dependencies(project, graph: StoryGraph, scene_id: str) -> Dependency:
    """
    Work out what else in the book leans on this scene.

    The useful question is not "what does this scene contain" but "what did
    this scene establish that a later scene assumes". So the interesting set is
    entities *first introduced here* which then recur - delete the scene and
    those later appearances lose their setup.
    """
    result = Dependency(scene_id=scene_id)
    data = project.data
    position = graph.scene_order.get(scene_id)
    if position is None:
        return result

    # One entity can reach a scene by several edges at once - declared, POV and
    # detected in the prose. Without deduplicating, it is counted three times
    # and the warning reads "24 later scenes" for a book that has five.
    seen: Set[str] = set()
    for edge in graph.out_edges(scene_id, ("linked", "pov", "mentions")):
        entity_id = edge.target
        if entity_id in seen or entity_id not in graph.nodes:
            continue
        seen.add(entity_id)
        appearances = graph.scenes_with(entity_id)
        if not appearances:
            continue
        if appearances[0] == scene_id:
            result.introduces.append(entity_id)
            later = [s for s in appearances
                     if graph.scene_order.get(s, 0) > position]
            if later:
                result.dependents.append((entity_id, later))
        if appearances == [scene_id]:
            result.only_appearance.append(entity_id)

    result.events = [e.source for e in graph.in_edges(scene_id, ("covers",))
                     if graph.nodes.get(e.source, Node("", "", "")).kind == "event"]
    result.beats = [e.source for e in graph.in_edges(scene_id, ("covers",))
                    if graph.nodes.get(e.source, Node("", "", "")).kind == "beat"]
    result.notes = [e.source for e in graph.in_edges(scene_id, ("references",))]
    return result


def dependency_text(project, graph: StoryGraph, scene_id: str) -> str:
    data = project.data
    scene = data.scene(scene_id)
    if not scene:
        return "That scene is no longer in the project."
    dep = dependencies(project, graph, scene_id)

    def label(node_id: str) -> str:
        node = graph.nodes.get(node_id)
        return node.name if node else "(unknown)"

    verdict = {
        "high": "Deleting this would break things.",
        "medium": "Deleting this needs care.",
        "low": "Nothing else depends on this scene.",
    }[dep.risk]

    lines = [
        "SCENE DEPENDENCIES",
        "=" * 60,
        scene.display,
        f"Scene {graph.scene_order.get(scene_id, 0) + 1} of "
        f"{len(graph.reading_order)}  -  {scene.word_count:,} words",
        "",
        verdict,
        "",
    ]

    if dep.introduces:
        lines += ["-" * 60, "FIRST INTRODUCED HERE", "-" * 60, ""]
        for entity_id in dep.introduces:
            lines.append(f"  {label(entity_id)}")
        lines.append("")

    if dep.dependents:
        lines += ["-" * 60, "LATER SCENES THAT ASSUME IT", "-" * 60, "",
                  "  These scenes use something this one introduces. If this",
                  "  scene goes, they lose their setup.", ""]
        for entity_id, later in sorted(dep.dependents,
                                       key=lambda p: -len(p[1])):
            lines.append(f"  {label(entity_id)}  ->  {len(later)} later scenes")
            for scene_ref in later[:8]:
                node = graph.nodes.get(scene_ref)
                number = graph.scene_order.get(scene_ref, 0) + 1
                lines.append(f"      {number:>3}. {node.name if node else '?'}")
            if len(later) > 8:
                lines.append(f"           ... and {len(later) - 8} more")
            lines.append("")

    if dep.only_appearance:
        lines += ["-" * 60, "ONLY APPEARS HERE", "-" * 60, "",
                  "  Delete this scene and these leave the book entirely.", ""]
        for entity_id in dep.only_appearance:
            lines.append(f"  {label(entity_id)}")
        lines.append("")

    if dep.events or dep.beats or dep.notes:
        lines += ["-" * 60, "ALSO ATTACHED", "-" * 60, ""]
        for event_id in dep.events:
            lines.append(f"  Timeline event   {label(event_id)}")
        for beat_id in dep.beats:
            lines.append(f"  Structural beat  {label(beat_id)}")
        for note_id in dep.notes:
            lines.append(f"  Research note    {label(note_id)}")
        lines.append("")

    if not (dep.introduces or dep.dependents or dep.only_appearance
            or dep.events or dep.beats or dep.notes):
        lines += ["Nothing in the book refers back to this scene. It can be cut",
                  "or moved without consequences elsewhere.", ""]
    return "\n".join(lines)


def deletion_warning(project, graph: StoryGraph, scene_id: str) -> str:
    """One short paragraph for the delete confirmation, or '' if it is safe."""
    dep = dependencies(project, graph, scene_id)
    if dep.risk == "low":
        return ""
    parts: List[str] = []
    if dep.dependents:
        names = ", ".join(
            graph.nodes[e].name for e, _ in dep.dependents[:3]
            if e in graph.nodes
        )
        # Distinct scenes, not the sum per entity - one later scene using three
        # things this scene introduced is still one scene at risk.
        affected = {s for _, later in dep.dependents for s in later}
        parts.append(
            f"{len(affected)} later "
            f"{'scene relies' if len(affected) == 1 else 'scenes rely'} on what "
            f"it introduces ({names})."
        )
    if dep.only_appearance:
        names = ", ".join(graph.nodes[e].name for e in dep.only_appearance[:3]
                          if e in graph.nodes)
        parts.append(f"{names} appear nowhere else.")
    if dep.events:
        parts.append(f"{len(dep.events)} timeline events point at it.")
    return " ".join(parts)


# --------------------------------------------------------------------------
# Relationship timeline
# --------------------------------------------------------------------------


@dataclass
class Pairing:
    a: str
    b: str
    scenes: List[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.scenes)


def relationship_timeline(project, graph: StoryGraph,
                          minimum: int = 2) -> List[Pairing]:
    """
    Every character pair that shares at least `minimum` scenes, with the scenes
    they share. Rendered as a strip this shows a relationship starting, running
    hot, going quiet and coming back - which a static web cannot show at all.
    """
    characters = [e.id for e in project.data.entities_of("character")]
    present: Dict[str, Set[str]] = {}
    for scene_id in graph.reading_order:
        here = {e.target for e in graph.out_edges(scene_id,
                                                  ("linked", "pov", "mentions"))}
        present[scene_id] = here & set(characters)

    pairs: Dict[Tuple[str, str], Pairing] = {}
    for scene_id in graph.reading_order:
        here = sorted(present.get(scene_id, ()))
        for i, a in enumerate(here):
            for b in here[i + 1:]:
                key = (a, b)
                pairs.setdefault(key, Pairing(a, b)).scenes.append(scene_id)

    result = [p for p in pairs.values() if p.count >= minimum]
    result.sort(key=lambda p: -p.count)
    return result


def relationship_timeline_text(project, graph: StoryGraph) -> str:
    data = project.data
    pairs = relationship_timeline(project, graph)
    width = 50
    total = max(1, len(graph.reading_order))

    header = f"  {'':28s} start" + " " * (width - 8) + "end"
    lines = [
        "RELATIONSHIP TIMELINE",
        "=" * (width + 38),
        data.title,
        "",
        "Each row is a pair of characters. The strip runs from the first page",
        "to the last; a filled block means they share that part of the book.",
        "Gaps are where a relationship goes quiet.",
        "",
        header,
        "",
    ]
    if not pairs:
        lines.append("  No two characters share enough scenes yet.")
        return "\n".join(lines)

    for pair in pairs[:40]:
        a = data.entity(pair.a)
        b = data.entity(pair.b)
        if not a or not b:
            continue
        # Each scene fills the whole slice of the strip it occupies rather
        # than a single character. On a six-scene draft single marks are so
        # far apart the shape of the relationship is invisible.
        strip = [" "] * width
        for scene_id in pair.scenes:
            index = graph.scene_order.get(scene_id, 0)
            start = int(index / total * width)
            end = max(start + 1, int((index + 1) / total * width))
            for column in range(start, min(end, width)):
                strip[column] = "#"
        label = f"{a.name} + {b.name}"
        if len(label) > 27:
            label = label[:26] + "."
        lines.append(f"  {label:28s}|{''.join(strip)}|  {pair.count:>3}")

    lines += ["", "-" * (width + 38), "",
              "Pairs are ordered by how many scenes they share.",
              f"The book is {len(graph.reading_order)} scenes wide."]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Story bible
# --------------------------------------------------------------------------


def write_story_bible(project, graph: Optional[StoryGraph] = None,
                      destination: Optional[Path] = None) -> Path:
    """
    Generate the complete reference guide, in Word, from what is actually in
    the manuscript - not from what was typed into a template a year ago.

    Regenerating it is always safe: the file is written whole each time and
    holds nothing the rest of the project does not already hold.
    """
    graph = graph or build(project)
    data = project.data

    doc = docxio.sheet_document()
    docxio.add_title_block(
        doc,
        f"{data.title} - Story Bible",
        data.subtitle or data.author,
        "GENERATED REFERENCE",
    )
    docxio.add_note(
        doc,
        "Generated from the manuscript and the project manifest. Anything you "
        "change here will be overwritten next time it is generated - edit the "
        "character sheets and scene cards instead.",
    )

    # -- the book at a glance --------------------------------------------
    doc.add_heading("The book at a glance", level=1)
    words = data.word_count
    glance = [
        ["Title", data.title],
        ["Author", data.author or "-"],
        ["Series", f"{data.series} #{data.book_number}" if data.series else "-"],
        ["Genre", data.genre or "-"],
        ["Logline", data.logline or "-"],
        ["Point of view", data.pov_style],
        ["Tense", data.tense],
        ["Structure", data.structure.replace("_", " ").title()],
        ["Length", f"{words:,} words in {len(data.scenes)} scenes, "
                   f"{len(data.chapters)} chapters"],
        ["Target", f"{data.targets.total_words:,} words"],
    ]
    docxio.add_data_table(doc, ["", ""], glance, widths=[1.4, 4.6])

    # -- cast -------------------------------------------------------------
    for entity_type in ("character", "location", "item", "faction", "thread"):
        entities = data.entities_of(entity_type)
        if not entities:
            continue
        doc.add_heading(ENTITY_PLURAL.get(entity_type, entity_type), level=1)
        rows = []
        for entity in entities:
            appearances = graph.scenes_with(entity.id)
            first = graph.nodes.get(appearances[0]).name if appearances else "-"
            last = graph.nodes.get(appearances[-1]).name if appearances else "-"
            rows.append([
                entity.name,
                entity.role or "-",
                entity.summary or "-",
                str(len(appearances)),
                first,
                last,
            ])
        docxio.add_data_table(
            doc,
            ["Name", "Role", "In one line", "Scenes", "First seen", "Last seen"],
            rows,
            widths=[1.1, 0.9, 1.9, 0.5, 0.85, 0.85],
        )

        # The full sheet contents, for characters only - the others rarely
        # have enough on them to be worth the pages.
        if entity_type == "character":
            for entity in entities:
                fields = {}
                try:
                    fields = project.entity_fields(entity.id)
                except Exception:
                    fields = {}
                filled = {k: v for k, v in fields.items() if v.strip()}
                if not filled:
                    continue
                doc.add_heading(entity.name, level=2)
                for key, value in filled.items():
                    paragraph = doc.add_paragraph()
                    run = paragraph.add_run(f"{key}: ")
                    run.bold = True
                    paragraph.add_run(value.replace("\n", "  |  "))

    # -- relationships ----------------------------------------------------
    pairs = relationship_timeline(project, graph)
    if pairs:
        doc.add_heading("Who knows whom", level=1)
        rows = []
        for pair in pairs[:60]:
            a, b = data.entity(pair.a), data.entity(pair.b)
            if not a or not b:
                continue
            first = graph.nodes.get(pair.scenes[0])
            last = graph.nodes.get(pair.scenes[-1])
            rows.append([a.name, b.name, str(pair.count),
                         first.name if first else "-",
                         last.name if last else "-"])
        docxio.add_data_table(
            doc, ["", "and", "Shared scenes", "First together", "Last together"],
            rows, widths=[1.2, 1.2, 0.9, 1.35, 1.35],
        )

    # -- structure --------------------------------------------------------
    if data.beats:
        doc.add_heading("Structure", level=1)
        rows = []
        for beat in sorted(data.beats, key=lambda b: b.order):
            linked = ", ".join(
                data.scene(s).display for s in beat.scene_ids if data.scene(s)
            )
            rows.append([
                beat.name,
                f"{int(beat.pct * 100)}%" if beat.pct is not None else "-",
                (beat.answer or "-")[:300],
                linked or "-",
                "yes" if beat.done else "",
            ])
        docxio.add_data_table(
            doc, ["Beat", "At", "Plan", "Scenes", "Written"], rows,
            widths=[1.1, 0.4, 2.3, 1.6, 0.6],
        )

    # -- chapters and scenes ----------------------------------------------
    doc.add_heading("Chapters and scenes", level=1)
    for chapter in data.ordered_chapters():
        scenes = data.scenes_in(chapter.id)
        doc.add_heading(
            f"{chapter.display}  ({sum(s.word_count for s in scenes):,} words)",
            level=2,
        )
        if chapter.synopsis.strip():
            doc.add_paragraph(chapter.synopsis.strip())
        rows = []
        for scene in scenes:
            pov = data.entity(scene.pov_id)
            people = ", ".join(
                data.entity(c).name for c in scene.character_ids
                if data.entity(c)
            )
            rows.append([
                scene.display,
                scene.status,
                f"{scene.word_count:,}",
                pov.name if pov else "-",
                people or "-",
                (scene.synopsis or "-")[:240],
            ])
        if rows:
            docxio.add_data_table(
                doc, ["Scene", "Status", "Words", "POV", "Who else", "Synopsis"],
                rows, widths=[1.2, 0.65, 0.5, 0.8, 1.15, 1.7],
            )

    # -- chronology -------------------------------------------------------
    events = project.ordered_events()
    if events:
        doc.add_heading("Chronology", level=1)
        rows = []
        for event in events:
            who = ", ".join(data.entity(c).name for c in event.character_ids
                            if data.entity(c))
            where = data.entity(event.location_id)
            scene = data.scene(event.scene_id)
            rows.append([event.story_date or "-", event.title, event.kind,
                         who or "-", where.name if where else "-",
                         scene.display if scene else "-",
                         "on page" if event.on_page else "backstory"])
        docxio.add_data_table(
            doc, ["When", "Event", "Kind", "Who", "Where", "Scene", "Seen?"],
            rows, widths=[0.85, 1.6, 0.6, 1.1, 0.9, 1.05, 0.7],
        )

    # -- research ---------------------------------------------------------
    if data.notes:
        doc.add_heading("Notes and research", level=1)
        rows = []
        for note in sorted(data.notes, key=lambda n: n.order):
            links = ", ".join(
                graph.nodes[t].name
                for t in (getattr(note, "links", []) or [])
                if t in graph.nodes
            )
            rows.append([note.title, note.kind, links or "-"])
        docxio.add_data_table(doc, ["Note", "Kind", "Linked to"], rows,
                              widths=[2.4, 1.0, 2.6])

    # -- maps -------------------------------------------------------------
    try:
        maps = sorted(project.folder("maps").glob("*.json"))
    except Exception:
        maps = []
    if maps:
        doc.add_heading("Maps", level=1)
        for path in maps:
            doc.add_paragraph(path.stem, style="List Bullet")

    from .atomic import save_via_atomic

    target = Path(destination) if destination else (
        project.folder("outline") / "Story Bible.docx"
    )
    return save_via_atomic(target, doc.save)


# --------------------------------------------------------------------------
# Ask your story - an offline question answerer
# --------------------------------------------------------------------------

_STOPWORDS = {
    "what", "who", "where", "when", "which", "how", "why", "does", "do", "did",
    "is", "are", "was", "were", "the", "a", "an", "in", "on", "of", "to", "for",
    "my", "me", "i", "it", "and", "or", "there", "their", "them", "this",
    "that", "about", "with", "many", "much", "first", "last", "story", "book",
    "novel", "tell", "show", "list", "give", "appear", "appears", "happen",
    "happens", "know", "knows", "have", "has", "any", "all", "can", "you",
}


def _resolve_entity(project, graph: StoryGraph, question: str):
    """Find which entity a question is about, preferring the longest match."""
    lowered = question.lower()
    best = None
    best_len = 0
    for name, ids in graph.name_lookup.items():
        if len(name) <= best_len:
            continue
        if re.search(r"\b" + re.escape(name) + r"\b", lowered):
            best, best_len = ids[0], len(name)
    return project.data.entity(best) if best else None


def answer(project, graph: StoryGraph, question: str) -> str:
    """
    Answer a question about the novel from the graph and the manuscript.

    This is a structured query engine, not a chat model: it recognises the
    shapes of question a story graph can actually answer, and falls back to a
    full-text search when it cannot. That means it never invents a fact, never
    needs the internet, and never sends your book anywhere - and it is instant.
    """
    data = project.data
    text = question.strip()
    if not text:
        return "Ask something about your story."
    lowered = text.lower()
    entity = _resolve_entity(project, graph, text)

    def scene_line(scene_id: str) -> str:
        node = graph.nodes.get(scene_id)
        scene = data.scene(scene_id)
        chapter = data.chapter(scene.chapter_id) if scene else None
        number = graph.scene_order.get(scene_id, 0) + 1
        return (f"  {number:>3}. {node.name if node else '?'}"
                f"{'   (' + chapter.display + ')' if chapter else ''}")

    # -- counting questions -----------------------------------------------
    if re.search(r"\bhow (many|long|much)\b", lowered) and not entity:
        return "\n".join([
            f"{data.title}",
            "",
            f"  {data.word_count:,} words",
            f"  {len(data.chapters)} chapters",
            f"  {len(data.scenes)} scenes",
            f"  {len(data.entities_of('character'))} characters",
            f"  {len(data.entities_of('location'))} locations",
            f"  {len(data.events)} timeline events",
            f"  {len(data.notes)} notes",
            "",
            f"  Target is {data.targets.total_words:,} words - "
            f"{data.word_count * 100 // max(1, data.targets.total_words)}% there.",
        ])

    # -- unresolved / loose ends -------------------------------------------
    if re.search(r"\b(unresolved|loose end|open|forgotten|hanging|missing)\b",
                 lowered):
        issues = check_continuity(project, graph)
        open_ones = [i for i in issues
                     if i.category in ("Open thread", "Unfinished", "Chekhov",
                                       "Unused")]
        if not open_ones:
            return "Nothing looks unresolved. No open threads, no leftover tags."
        lines = ["Still open:", ""]
        for issue in open_ones[:25]:
            lines.append(f"  {issue.title}")
        return "\n".join(lines)

    # -- questions about a specific thing ----------------------------------
    if entity:
        appearances = graph.scenes_with(entity.id)
        lines = [f"{entity.name}",
                 f"{ENTITY_LABELS.get(entity.type, entity.type)}"
                 + (f" - {entity.role}" if entity.role else ""), ""]
        if entity.summary:
            lines += [entity.summary, ""]

        if re.search(r"\b(who|what) (is|are|was)\b", lowered) or \
           re.search(r"\btell me about\b", lowered):
            try:
                fields = {k: v for k, v in project.entity_fields(entity.id).items()
                          if v.strip()}
            except Exception:
                fields = {}
            if fields:
                for key, value in list(fields.items())[:20]:
                    lines.append(f"  {key}: {value.replace(chr(10), ' | ')[:200]}")
                lines.append("")

        if re.search(r"\b(first|introduce)\b", lowered) and appearances:
            first = appearances[0]
            lines += [f"First appears in:", scene_line(first),
                      f"  ({int(graph.position(first) * 100)}% into the book)", ""]
            return "\n".join(lines)

        if re.search(r"\blast\b", lowered) and appearances:
            lines += ["Last appears in:", scene_line(appearances[-1]), ""]
            return "\n".join(lines)

        if re.search(r"\b(meet|know|with|together|relationship)\b", lowered):
            shared = graph.co_occurring(entity.id)
            people = [(data.entity(i), n) for i, n in shared.most_common(20)]
            people = [(e, n) for e, n in people if e and e.type == "character"]
            if people:
                lines.append("Shares scenes with:")
                for other, count in people:
                    lines.append(f"  {other.name:<28s} {count} scenes")
                lines.append("")
            return "\n".join(lines)

        if not appearances:
            lines.append("Does not appear in any scene yet.")
            return "\n".join(lines)

        lines.append(f"Appears in {len(appearances)} of "
                     f"{len(graph.reading_order)} scenes:")
        for scene_id in appearances[:30]:
            lines.append(scene_line(scene_id))
        if len(appearances) > 30:
            lines.append(f"       ... and {len(appearances) - 30} more")
        lines.append("")

        shared = graph.co_occurring(entity.id)
        people = [(data.entity(i), n) for i, n in shared.most_common(8)]
        people = [(e, n) for e, n in people if e and e.type == "character"]
        if people:
            lines.append("Most often with: " +
                         ", ".join(f"{e.name} ({n})" for e, n in people))
        return "\n".join(lines)

    # -- chapter questions --------------------------------------------------
    chapter_match = re.search(r"\bchapter\s+(\d+)\b", lowered)
    if chapter_match:
        index = int(chapter_match.group(1)) - 1
        chapters = data.ordered_chapters()
        if 0 <= index < len(chapters):
            chapter = chapters[index]
            scenes = data.scenes_in(chapter.id)
            lines = [chapter.display, ""]
            if chapter.synopsis.strip():
                lines += [chapter.synopsis.strip(), ""]
            for scene in scenes:
                pov = data.entity(scene.pov_id)
                lines.append(f"  {scene.display}  ({scene.word_count:,} words"
                             + (f", POV {pov.name}" if pov else "") + ")")
                if scene.synopsis.strip():
                    for chunk in _wrap(scene.synopsis.strip(), 62):
                        lines.append(f"      {chunk}")
            return "\n".join(lines)
        return f"There is no chapter {index + 1}. The book has {len(chapters)}."

    # -- fall back to full-text search --------------------------------------
    terms = [w for w in re.findall(r"[a-z']{3,}", lowered)
             if w not in _STOPWORDS]
    if not terms:
        return ("I could not tell what that is about. Try a name, "
                "'chapter 4', 'how long is the book', or 'what is unresolved'.")

    needle = max(terms, key=len)
    hits = project.search(needle, limit=40)
    if not hits:
        return (f"Nothing in the manuscript, the sheets or the notes contains "
                f"'{needle}'.")
    lines = [f"{len(hits)} places mention '{needle}':", ""]
    for kind, name, snippet in hits[:25]:
        lines.append(f"  [{kind}] {name}")
        for chunk in _wrap(snippet.strip(), 62):
            lines.append(f"      {chunk}")
        lines.append("")
    return "\n".join(lines)


SUGGESTED_QUESTIONS = [
    "How long is the book?",
    "What is unresolved?",
    "Where does <name> first appear?",
    "Who does <name> meet?",
    "Tell me about <name>",
    "What happens in chapter 3?",
]


# --------------------------------------------------------------------------
# Graph overview, for the browser
# --------------------------------------------------------------------------


def verify_project(project, graph: Optional[StoryGraph] = None) -> Tuple[str, int]:
    """
    The one-button project check: what is here, what is wrong, out of 100.

    Returns (report, score). The score is deliberately generous about craft
    opinions and harsh about broken data: a plot thread you chose to drop is
    your business, a scene pointing at a character that no longer exists is
    not.
    """
    graph = graph or build(project)
    data = project.data
    issues = check_continuity(project, graph)

    # -- structural faults the continuity checker does not cover ----------
    structural: List[Issue] = []

    seen_ids: Dict[str, str] = {}
    for kind, items in (("scene", data.scenes), ("chapter", data.chapters),
                        ("entity", data.entities), ("note", data.notes),
                        ("event", data.events)):
        for item in items:
            if item.id in seen_ids:
                structural.append(Issue(
                    "high", "Duplicate id",
                    f"Two {kind}s share the id {item.id}",
                    "Only one of them can be found by anything that links to "
                    "it. Rename or recreate one.",
                ))
            seen_ids[item.id] = kind

    try:
        missing = project.missing_files()
    except Exception:
        missing = []
    for kind, name in missing:
        structural.append(Issue(
            "high", "Missing file",
            f"{kind} '{name}' has no document on disk",
            "The manifest points at a file that is not there. It may have "
            "been moved or deleted outside the tool.",
            name,
        ))

    for scene in data.scenes:
        if scene.chapter_id and not data.chapter(scene.chapter_id):
            structural.append(Issue(
                "high", "Orphan scene",
                f"'{scene.display}' belongs to a chapter that is gone",
                "It still compiles, at the end, but it is no longer part of "
                "any chapter.",
                scene.display,
            ))

    titles: Dict[str, int] = {}
    for chapter in data.chapters:
        key = chapter.display.strip().lower()
        titles[key] = titles.get(key, 0) + 1
    for title, count in titles.items():
        if count > 1:
            structural.append(Issue(
                "medium", "Duplicate title",
                f"{count} chapters are called '{title}'",
                "Not an error, but the compiled manuscript and the binder "
                "become hard to navigate.",
            ))

    for pin_file in (project.folder("maps").glob("*.json")
                     if project.folder("maps").exists() else []):
        try:
            from .mapmaker import load_map

            if load_map(pin_file) is None:
                raise ValueError("unreadable")
        except Exception:
            structural.append(Issue(
                "medium", "Unreadable map",
                f"Map '{pin_file.stem}' could not be opened",
                "The file may be damaged. A backup copy may still be good.",
                pin_file.stem,
            ))
    # Broken pin links are reported by the map checks in check_continuity.

    everything = sorted(structural + issues, key=lambda i: (i.rank, i.category))

    # -- score -------------------------------------------------------------
    counts = Counter(i.severity for i in everything)
    penalty = counts.get("high", 0) * 6 + counts.get("medium", 0) * 2 \
        + counts.get("low", 0) * 0.25
    score = int(max(0, min(100, round(100 - penalty))))

    # -- report ------------------------------------------------------------
    words = data.word_count
    lines = [
        "PROJECT VERIFICATION",
        "=" * 62,
        data.title + (f" - {data.author}" if data.author else ""),
        "",
        "WHAT IS HERE",
        "-" * 62,
        f"  {len(data.chapters):>6,}  chapters",
        f"  {len(data.scenes):>6,}  scenes",
        f"  {len(data.entities_of('character')):>6,}  characters",
        f"  {len(data.entities_of('location')):>6,}  locations",
        f"  {len(data.entities_of('item')):>6,}  items",
        f"  {len(data.entities_of('faction')):>6,}  factions",
        f"  {len(data.entities_of('thread')):>6,}  plot threads",
        f"  {len(data.notes):>6,}  notes and research",
        f"  {len(data.events):>6,}  timeline events",
        f"  {words:>6,}  words",
        "",
        f"  {stats_line(project, graph)}",
        "",
    ]

    if not everything:
        lines += ["-" * 62, "",
                  "Nothing to report. Every file is present, every link "
                  "resolves,", "and the chronology is consistent.", ""]
    else:
        for severity, heading in (("high", "PROBLEMS"),
                                  ("medium", "WARNINGS"),
                                  ("low", "MINOR")):
            group = [i for i in everything if i.severity == severity]
            if not group:
                continue
            lines += ["-" * 62, f"{heading}  ({len(group)})", "-" * 62, ""]
            for issue in group[:60]:
                lines.append(f"  {'!' if severity == 'high' else '-'} "
                             f"{issue.title}")
                for chunk in _wrap(issue.detail, 58):
                    lines.append(f"      {chunk}")
                lines.append("")
            if len(group) > 60:
                lines.append(f"  ... and {len(group) - 60} more not listed.")
                lines.append("")

    bar_width = 40
    filled = int(round(score / 100 * bar_width))
    lines += [
        "=" * 62,
        "",
        f"  HEALTH SCORE   {score}/100",
        f"  [{'#' * filled}{'.' * (bar_width - filled)}]",
        "",
        f"  {counts.get('high', 0)} problems, {counts.get('medium', 0)} "
        f"warnings, {counts.get('low', 0)} minor notes.",
        "",
        "  Problems are broken data - links to things that no longer exist,",
        "  files that are not on disk. Those are worth fixing.",
        "  Warnings and minor notes are opinions about the writing, and a",
        "  deliberate choice will often trip one. Nothing here is an order.",
        "",
    ]
    return "\n".join(lines), score


def stats_line(project, graph: StoryGraph) -> str:
    from . import stats

    words = project.data.word_count
    scenes = len(project.data.scenes)
    average = words // scenes if scenes else 0
    return (f"About {stats.reading_time(words)} of reading, "
            f"averaging {average:,} words a scene.")


def overview_text(project, graph: StoryGraph) -> str:
    data = project.data
    lines = [
        "STORY KNOWLEDGE GRAPH",
        "=" * 66,
        data.title,
        "",
        f"{len(graph.nodes)} things, {len(graph.edges)} connections between them.",
        "",
        "Built by reading every scene once and locating every name and alias",
        "in it. Links you declared and names found in the prose are both here;",
        "the second kind is how the tool notices what you forgot to link.",
        "",
    ]
    counts = Counter(n.kind for n in graph.nodes.values())
    for kind, count in counts.most_common():
        lines.append(f"  {count:>4}  {ENTITY_PLURAL.get(kind, kind.title() + 's')}")
    lines.append("")

    explicit = sum(1 for e in graph.edges if e.explicit)
    lines += [
        f"  {explicit} links you declared",
        f"  {len(graph.edges) - explicit} found in the prose",
        "",
        "-" * 66,
        "MOST CONNECTED",
        "-" * 66,
        "",
    ]
    degree: Counter = Counter()
    for edge in graph.edges:
        degree[edge.source] += 1
        degree[edge.target] += 1
    for node_id, count in degree.most_common(20):
        node = graph.nodes.get(node_id)
        if not node or node.kind in ("chapter", "beat"):
            continue
        lines.append(f"  {count:>4}  {node.name}   ({node.label})")
    return "\n".join(lines)
