"""
The editor's knowledge of the novel it is editing.

A general English dictionary is the wrong tool for a fantasy manuscript. It
does not know Aethermoor, it will never know Aethermoor, and it will underline
it four thousand times. Meanwhile the thing it *could* usefully catch - that
you wrote "Iron Hold" in chapter nine when every other chapter says "Iron
Keep" - is invisible to it, because both are equally unknown.

So this builds a dictionary from the book itself:

    build(project)                 the project's own vocabulary
    lex.complete("King Ro")        -> King Roland, King Rowan
    lex.next_words("she walked into the")  -> room, hall, forest
    lex.near_miss("Iron Hold")     -> Iron Keep
    lex.accept("Aethermoor")       never questioned again

Every one of these comes from the manuscript and the project's own sheets.
Nothing is downloaded, nothing is installed, and it works on the first day of
a new novel with three names in it - it simply knows less.

What this deliberately is not: a general spell checker. Telling the difference
between "recieve" and a place you invented needs a word list of real English,
which is a file this tool does not ship. The half that needs no such file is
the half that no other writing tool does well, so that is the half built here.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

#: Words that start sentences and so appear capitalised without being names.
_SENTENCE_STARTERS = {
    "the", "a", "an", "and", "but", "for", "he", "she", "it", "they", "we",
    "you", "i", "his", "her", "their", "there", "then", "when", "where",
    "what", "who", "why", "how", "if", "so", "no", "yes", "not", "this",
    "that", "these", "those", "at", "in", "on", "of", "to", "by", "with",
    "from", "as", "was", "were", "is", "are", "had", "has", "have", "did",
    "do", "does", "one", "two", "all", "some", "after", "before", "once",
    "again", "still", "even", "only", "just", "now", "here", "outside",
    "inside", "above", "below", "behind", "beyond", "beneath", "across",
}

_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
#: A capitalised run: "Iron Keep", "King Roland of the North" stops at "of".
_PROPER = re.compile(r"\b[A-Z][a-z'\-]+(?:\s+[A-Z][a-z'\-]+)*")


def _distance(a: str, b: str, limit: int = 3) -> int:
    """
    Levenshtein distance, abandoned once it passes `limit`.

    Bailing early matters: this runs against every name in the project for
    every suspicious word, and the answers beyond three edits are never used.
    """
    if a == b:
        return 0
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        best = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            value = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            current.append(value)
            best = min(best, value)
        if best > limit:
            return limit + 1
        previous = current
    return previous[-1]


@dataclass
class Term:
    """One thing the book knows about."""

    text: str
    kind: str                  # character | location | item | faction | thread
                               # | alias | invented | accepted
    entity_id: str = ""
    count: int = 0

    @property
    def sort_key(self) -> Tuple:
        # Declared names before words merely spotted in the prose.
        rank = 0 if self.kind not in ("invented", "accepted") else 1
        return (rank, -self.count, self.text.lower())


@dataclass
class Lexicon:
    """Everything the editor knows about this particular novel."""

    terms: Dict[str, Term] = field(default_factory=dict)
    #: lowercase word -> how often it appears in the manuscript
    frequency: Counter = field(default_factory=Counter)
    #: "she walked into" -> Counter of what came next
    following: Dict[str, Counter] = field(default_factory=dict)
    #: Words the writer has explicitly accepted.
    accepted: Set[str] = field(default_factory=set)
    scanned_scenes: int = 0

    # -- lookups ---------------------------------------------------------
    def knows(self, word: str) -> bool:
        key = word.lower()
        return (key in self.terms or key in self.accepted
                or key in self.frequency)

    def term(self, word: str) -> Optional[Term]:
        return self.terms.get(word.lower())

    def names(self) -> List[Term]:
        return sorted(self.terms.values(), key=lambda t: t.sort_key)

    # -- completion ------------------------------------------------------
    def complete(self, prefix: str, limit: int = 8) -> List[str]:
        """
        What the writer is probably typing.

        Declared names come first and are ranked by how often the book uses
        them, so "King Ro" offers the king who is actually in the story rather
        than the one mentioned once in chapter two.
        """
        prefix = prefix.strip()
        if len(prefix) < 2:
            return []
        lowered = prefix.lower()
        hits: List[Tuple[Tuple, str]] = []
        seen: Set[str] = set()

        for term in self.terms.values():
            if term.text.lower().startswith(lowered) \
                    and term.text.lower() != lowered:
                if term.text.lower() in seen:
                    continue
                seen.add(term.text.lower())
                hits.append((term.sort_key, term.text))

        # Then ordinary words from the manuscript, which is how a writer's own
        # vocabulary - "gloaming", "portcullis" - stops being retyped.
        if len(hits) < limit:
            for word, count in self.frequency.most_common():
                key = word.lower()
                if key.startswith(lowered) and key != lowered \
                        and key not in seen:
                    seen.add(key)
                    hits.append(((2, -count, key), word))
                if len(hits) >= limit * 3:
                    break

        hits.sort(key=lambda pair: pair[0])
        return [text for _key, text in hits[:limit]]

    # -- prediction ------------------------------------------------------
    def next_words(self, text: str, limit: int = 6) -> List[str]:
        """
        What usually follows this phrase, in this book.

        A plain trigram count. It is not a language model and does not
        pretend to be: it can only offer what the writer has already written
        somewhere, which is exactly what makes it safe.
        """
        words = _WORD.findall(text.lower())
        for size in (2, 1):
            if len(words) < size:
                continue
            key = " ".join(words[-size:])
            counts = self.following.get(key)
            if counts:
                return [word for word, _n in counts.most_common(limit)]
        return []

    # -- consistency -----------------------------------------------------
    def near_miss(self, phrase: str, limit: int = 3) -> List[str]:
        """
        Names close to this one, when this one is not itself known.

        This is the check no general dictionary can make: "Iron Hold" is not a
        spelling mistake in any language, it is a mistake in *your* book.
        """
        phrase = phrase.strip()
        if not phrase or self.knows(phrase):
            return []
        lowered = phrase.lower()
        tokens = [t for t in lowered.split() if len(t) > 2
                  and t not in _SENTENCE_STARTERS]
        scored: List[Tuple[int, int, str]] = []

        for term in self.terms.values():
            other = term.text.lower()
            if other == lowered:
                return []
            other_tokens = [t for t in other.split() if len(t) > 2
                            and t not in _SENTENCE_STARTERS]

            # Straight misspelling: "Aethermor" for "Aethermoor".
            gap = _distance(lowered, other, limit=limit)
            if gap <= limit:
                scored.append((gap, -term.count, term.text))
                continue

            # The more interesting case, which edit distance cannot see:
            # "Iron Hold" for "Iron Keep". Four edits apart, so no spell
            # checker would connect them - but they share the distinctive
            # word "Iron", and one of them is not a place in this book.
            # That is a memory slip, not a typo, and it is exactly the kind
            # of thing that survives into print.
            if tokens and other_tokens and len(tokens) == len(other_tokens):
                shared = [t for t in tokens if t in other_tokens]
                if shared and len(shared) == len(tokens) - 1:
                    scored.append((limit + 1, -term.count, term.text))

        scored.sort()
        return [text for _gap, _count, text in scored[:limit]]

    def suspicious(self, text: str, limit: int = 40
                   ) -> List[Tuple[str, List[str]]]:
        """
        Capitalised phrases in `text` that look like a known name misspelt.

        Only capitalised runs are considered, because those are the ones that
        are supposed to be names. Anything already known, accepted, or with no
        close relative is left alone - a checker that flags every invented
        word is one that gets switched off in a week.
        """
        out: List[Tuple[str, List[str]]] = []
        seen: Set[str] = set()
        for match in _PROPER.finditer(text or ""):
            phrase = match.group(0)
            key = phrase.lower()
            if key in seen:
                continue
            # Remembered whether or not it matched. Only recording matches
            # meant every unmatched phrase - the great majority - paid for a
            # full Levenshtein scan against every name again on each of its
            # occurrences, which was over half the cost of the live check.
            seen.add(key)
            if self.knows(phrase):
                continue
            head = phrase.split()[0].lower()
            if len(phrase.split()) == 1 and head in _SENTENCE_STARTERS:
                continue
            close = self.near_miss(phrase)
            if close:
                out.append((phrase, close))
            if len(out) >= limit:
                break
        return out

    # -- learning --------------------------------------------------------
    def accept(self, word: str) -> None:
        cleaned = (word or "").strip()
        if cleaned:
            self.accepted.add(cleaned.lower())
            self.terms.setdefault(
                cleaned.lower(), Term(cleaned, "accepted", count=1))


# --------------------------------------------------------------------------
# Building
# --------------------------------------------------------------------------


def build(project, graph=None, max_scenes: int = 0) -> Lexicon:
    """
    Read the project and learn its vocabulary.

    Reuses the story graph's already-read prose when one is handed in, which
    makes this free at the point of use - the graph is built the moment any of
    the story windows open.
    """
    from . import docxio

    lex = Lexicon()
    data = project.data

    for entity in data.entities:
        if entity.name.strip():
            lex.terms[entity.name.lower()] = Term(
                entity.name.strip(), entity.type, entity.id)
        for alias in entity.aliases:
            if alias.strip() and alias.lower() not in lex.terms:
                lex.terms[alias.lower()] = Term(alias.strip(), "alias",
                                                entity.id)

    for word in getattr(data, "accepted_words", []) or []:
        lex.accept(word)

    scenes = data.ordered_scenes()
    if max_scenes:
        scenes = scenes[:max_scenes]

    proper_counts: Counter = Counter()
    following: Dict[str, Counter] = defaultdict(Counter)

    for scene in scenes:
        text = ""
        if graph is not None:
            text = graph.scene_text.get(scene.id, "")
        if not text and scene.docx:
            try:
                text = docxio.read_prose(project.abs(scene.docx))
            except Exception:
                text = ""
        if not text:
            continue
        lex.scanned_scenes += 1

        words = _WORD.findall(text)
        lex.frequency.update(w.lower() for w in words)

        # Only bigram context, and only after a word worth predicting from.
        #
        # Storing 1-, 2- and 3-word keys for every position built a table with
        # roughly three entries per word in the book: about 190 MB and three
        # seconds of frozen interface on a full novel, rebuilt every time the
        # writer paused. Two-word keys alone answer the same question - "what
        # follows this phrase" - at a fraction of the cost, and the single
        # word fallback below covers the rest.
        lowered = [w.lower() for w in words]
        for index in range(len(lowered) - 2):
            following[lowered[index] + " " + lowered[index + 1]][
                lowered[index + 2]] += 1
        for index in range(len(lowered) - 1):
            following[lowered[index]][lowered[index + 1]] += 1

        for match in _PROPER.finditer(text):
            phrase = match.group(0)
            # A capitalised word at the start of a sentence is usually just a
            # sentence. Require it either to be multi-word, or to appear
            # somewhere that is not a sentence opening.
            if len(phrase.split()) == 1:
                start = match.start()
                before = text[max(0, start - 2):start]
                if start == 0 or before.strip().endswith((".", "!", "?")) \
                        or "\n" in before:
                    continue
                if phrase.lower() in _SENTENCE_STARTERS:
                    continue
            proper_counts[phrase] += 1

    # A continuation seen once is not a pattern, and dropping those removes
    # the great majority of the table. Each surviving entry keeps only its
    # commonest handful, because nothing past the sixth is ever offered.
    lex.following = {
        key: Counter(dict(counts.most_common(6)))
        for key, counts in following.items()
        if sum(counts.values()) > 1
    }

    for phrase, count in proper_counts.items():
        key = phrase.lower()
        if key in lex.terms:
            lex.terms[key].count += count
            continue
        # Seen enough times to be a real name rather than a typo.
        if count >= 2:
            lex.terms[key] = Term(phrase, "invented", count=count)

    for term in lex.terms.values():
        if term.count == 0:
            term.count = lex.frequency.get(term.text.lower().split()[0], 0)

    return lex


def report(project, lex: Lexicon) -> str:
    """A readable summary of what the editor has learned."""
    names = lex.names()
    declared = [t for t in names if t.kind not in ("invented", "accepted")]
    invented = [t for t in names if t.kind == "invented"]
    accepted = [t for t in names if t.kind == "accepted"]

    lines = [
        "WHAT THE EDITOR KNOWS ABOUT THIS BOOK",
        "=" * 62,
        project.data.title,
        "",
        f"  {len(declared)} names from your sheets",
        f"  {len(invented)} more picked up from the prose",
        f"  {len(accepted)} you have accepted by hand",
        f"  {len(lex.frequency):,} distinct words across "
        f"{lex.scanned_scenes} scenes",
        f"  {len(lex.following):,} phrase continuations learned",
        "",
        "This is used for completion, for catching a name typed slightly",
        "wrong, and for leaving your invented words alone.",
        "",
    ]
    if declared:
        lines += ["-" * 62, "FROM YOUR SHEETS", "-" * 62, ""]
        for term in declared[:60]:
            lines.append(f"  {term.count:>5}  {term.text}   ({term.kind})")
        lines.append("")
    if invented:
        lines += ["-" * 62, "LEARNED FROM THE PROSE", "-" * 62, "",
                  "  Names you use but have not made a sheet for.", ""]
        for term in invented[:40]:
            lines.append(f"  {term.count:>5}  {term.text}")
        lines.append("")
    return "\n".join(lines)
