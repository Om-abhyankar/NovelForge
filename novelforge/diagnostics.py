"""
Prose diagnostics - a developmental and line editor that runs offline.

Every check is a heuristic, and heuristics are wrong sometimes. Findings are
worded as observations rather than corrections: the tool has no idea that your
narrator is deliberately verbose. Nothing here rewrites your text.

Checks are ordered from the ones worth acting on to the ones worth glancing at.
Everything runs on plain strings, so it works on a scene, a chapter, or the
whole compiled manuscript.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# Word lists
# --------------------------------------------------------------------------

FILLER_WORDS = {
    "very", "really", "quite", "rather", "somewhat", "somehow", "just",
    "actually", "basically", "literally", "totally", "completely", "absolutely",
    "definitely", "certainly", "probably", "perhaps", "maybe", "almost",
    "nearly", "practically", "virtually", "simply", "merely", "only",
    "even", "still", "already", "sort", "kind", "bit", "little", "lot",
    "much", "many", "some", "any", "thing", "things", "stuff", "began",
    "started", "suddenly", "immediately", "instantly", "finally", "then",
}

# Words that put a layer of narration between reader and experience.
FILTER_WORDS = {
    "saw", "watched", "noticed", "observed", "spotted", "glimpsed",
    "heard", "listened", "felt", "sensed", "smelled", "tasted",
    "realised", "realized", "knew", "thought", "wondered", "decided",
    "seemed", "appeared", "looked", "remembered", "recalled",
    "could see", "could hear", "could feel",
}

SAID_BOOKISMS = {
    "expostulated", "ejaculated", "chortled", "guffawed", "opined",
    "interjected", "articulated", "enunciated", "vociferated", "asseverated",
    "queried", "riposted", "quipped", "hissed", "growled", "barked",
    "snarled", "purred", "grated", "rasped", "chirped", "trilled",
    "simpered", "smirked", "grinned", "smiled", "laughed", "sighed",
    "shrugged", "nodded", "frowned", "beamed", "scowled",
}

# Things you cannot actually do to a sentence.
IMPOSSIBLE_TAGS = {
    "smiled", "grinned", "laughed", "nodded", "shrugged", "frowned",
    "sighed", "beamed", "scowled", "winced", "smirked",
}

CLICHES = [
    "at the end of the day", "avoid like the plague", "beat around the bush",
    "better late than never", "bite the bullet", "blessing in disguise",
    "blood ran cold", "calm before the storm", "cat got your tongue",
    "cold as ice", "cry over spilled milk", "dead as a doornail",
    "deafening silence", "easier said than done", "eyes like saucers",
    "face the music", "few and far between", "heart of gold",
    "heart pounding", "heart skipped a beat", "in the nick of time",
    "last but not least", "light as a feather", "needle in a haystack",
    "nip it in the bud", "only time will tell", "pale as a ghost",
    "piece of cake", "plain as day", "quiet as a mouse", "raining cats",
    "read between the lines", "rude awakening", "shot in the dark",
    "sight for sore eyes", "sigh of relief", "smooth as silk",
    "stopped dead in", "take it with a grain of salt", "the calm before",
    "thick as thieves", "time will tell", "tip of the iceberg",
    "under the weather", "white as a sheet", "without a doubt",
    "a shiver ran down", "let out a breath", "held her breath",
    "held his breath", "little did", "much to", "all hell broke loose",
]

BE_VERBS = {"is", "are", "was", "were", "be", "been", "being", "am"}

# Irregular past participles that do not end in -ed.
IRREGULAR_PARTICIPLES = {
    "born", "beaten", "become", "begun", "bent", "bitten", "blown", "broken",
    "brought", "built", "bought", "caught", "chosen", "come", "cut", "done",
    "drawn", "driven", "drunk", "eaten", "fallen", "felt", "fought", "found",
    "forgotten", "frozen", "given", "gone", "grown", "heard", "held", "hidden",
    "hit", "hurt", "kept", "known", "laid", "led", "left", "lent", "let",
    "lost", "made", "meant", "met", "paid", "put", "read", "ridden", "risen",
    "run", "said", "seen", "sold", "sent", "set", "shaken", "shot", "shown",
    "shut", "sung", "sunk", "sat", "slept", "spoken", "spent", "stolen",
    "struck", "sworn", "taken", "taught", "torn", "told", "thought", "thrown",
    "understood", "woken", "worn", "won", "written",
}

DIALOGUE_TAG_VERBS = {
    "said", "asked", "replied", "answered", "whispered", "shouted", "called",
    "murmured", "muttered", "added", "continued", "began", "explained",
    "admitted", "agreed", "insisted", "offered", "warned", "demanded",
    "wondered", "repeated", "breathed", "yelled", "screamed",
}

SENTENCE_END = re.compile(r"(?<=[.!?])[\"'”’]?\s+")
WORD_RE = re.compile(r"[A-Za-z'’]+")
DIALOGUE_RE = re.compile(r"[“\"]([^”\"]{2,})[”\"]")


# --------------------------------------------------------------------------
# Finding
# --------------------------------------------------------------------------


@dataclass
class Finding:
    check: str
    severity: str            # note | watch | flag
    message: str
    examples: List[str] = field(default_factory=list)
    count: int = 0

    def line(self) -> str:
        marker = {"flag": "!", "watch": "~", "note": "."}.get(self.severity, ".")
        return f"[{marker}] {self.message}"


@dataclass
class Report:
    words: int = 0
    sentences: int = 0
    paragraphs: int = 0
    findings: List[Finding] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

    def by_severity(self) -> List[Finding]:
        rank = {"flag": 0, "watch": 1, "note": 2}
        return sorted(self.findings, key=lambda f: (rank.get(f.severity, 3), -f.count))


# --------------------------------------------------------------------------
# Text splitting
# --------------------------------------------------------------------------


def sentences_of(text: str) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []
    parts = SENTENCE_END.split(cleaned)
    return [p.strip() for p in parts if p.strip()]


def words_of(text: str) -> List[str]:
    return WORD_RE.findall(text or "")


def paragraphs_of(text: str) -> List[str]:
    return [p.strip() for p in (text or "").split("\n\n") if p.strip()]


def count_syllables(word: str) -> int:
    """Vowel-group heuristic. Good enough for a readability index."""
    word = word.lower().strip("'’")
    if not word:
        return 0
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]es|[^laeiouy]e)$", "", word)
    word = re.sub(r"^y", "", word)
    groups = re.findall(r"[aeiouy]{1,2}", word)
    return max(1, len(groups))


# --------------------------------------------------------------------------
# Individual checks
# --------------------------------------------------------------------------


def check_adverbs(text: str) -> Optional[Finding]:
    words = words_of(text)
    if not words:
        return None
    # -ly words that are genuinely adjectives, not adverbs.
    exempt = {"only", "family", "reply", "supply", "apply", "imply", "ugly",
              "early", "likely", "lonely", "lovely", "silly", "holy", "italy",
              "assembly", "belly", "jelly", "rally", "really", "fully"}
    hits = [w for w in words if w.lower().endswith("ly")
            and w.lower() not in exempt and len(w) > 4]
    if not hits:
        return None
    rate = len(hits) / len(words) * 100
    common = Counter(h.lower() for h in hits).most_common(6)
    severity = "flag" if rate > 3.5 else "watch" if rate > 2.0 else "note"
    return Finding(
        "adverbs", severity,
        f"{len(hits)} -ly adverbs ({rate:.1f}% of words). "
        f"Under 2% reads clean; a strong verb usually beats verb-plus-adverb.",
        [f"{w} x{c}" for w, c in common],
        len(hits),
    )


def check_filler(text: str) -> Optional[Finding]:
    words = [w.lower() for w in words_of(text)]
    if not words:
        return None
    counts = Counter(w for w in words if w in FILLER_WORDS)
    total = sum(counts.values())
    if not total:
        return None
    rate = total / len(words) * 100
    severity = "flag" if rate > 6 else "watch" if rate > 3.5 else "note"
    return Finding(
        "filler", severity,
        f"{total} filler and hedging words ({rate:.1f}%). "
        f"Most can be deleted without changing the meaning.",
        [f"{w} x{c}" for w, c in counts.most_common(8)],
        total,
    )


def check_filter_words(text: str) -> Optional[Finding]:
    lowered = (text or "").lower()
    counts: Counter = Counter()
    for phrase in FILTER_WORDS:
        found = len(re.findall(rf"\b{re.escape(phrase)}\b", lowered))
        if found:
            counts[phrase] = found
    total = sum(counts.values())
    if not total:
        return None
    words = len(words_of(text)) or 1
    rate = total / words * 100
    severity = "watch" if rate > 1.5 else "note"
    return Finding(
        "filter", severity,
        f"{total} filter words. \"She saw the door open\" holds the reader "
        f"at arm's length; \"the door opened\" puts them in the room.",
        [f"{w} x{c}" for w, c in counts.most_common(8)],
        total,
    )


def check_passive(text: str) -> Optional[Finding]:
    sentences = sentences_of(text)
    if not sentences:
        return None
    hits: List[str] = []
    for sentence in sentences:
        tokens = words_of(sentence)
        for i, token in enumerate(tokens[:-1]):
            if token.lower() not in BE_VERBS:
                continue
            # Allow one adverb between the auxiliary and the participle.
            for offset in (1, 2):
                if i + offset >= len(tokens):
                    break
                candidate = tokens[i + offset].lower()
                if offset == 2 and not tokens[i + 1].lower().endswith("ly"):
                    break
                participle = (
                    candidate in IRREGULAR_PARTICIPLES
                    or (candidate.endswith("ed") and len(candidate) > 4)
                )
                if participle:
                    hits.append(sentence.strip()[:110])
                    break
            else:
                continue
            break
    if not hits:
        return None
    rate = len(hits) / len(sentences) * 100
    severity = "flag" if rate > 20 else "watch" if rate > 10 else "note"
    return Finding(
        "passive", severity,
        f"{len(hits)} possible passive constructions ({rate:.0f}% of "
        f"sentences). Passive is a tool, not a sin - but check each one is "
        f"deliberate.",
        hits[:5], len(hits),
    )


def check_said_bookisms(text: str) -> Optional[Finding]:
    lowered = (text or "").lower()
    counts: Counter = Counter()
    for verb in SAID_BOOKISMS:
        # Only count when it looks like a dialogue tag.
        found = len(re.findall(rf"[”\"],?\s*\w*\s*\b{verb}\b", lowered))
        found += len(re.findall(rf"\b{verb}\b\s*,?\s*[“\"]", lowered))
        if found:
            counts[verb] = found
    total = sum(counts.values())
    if not total:
        return None
    return Finding(
        "said_bookisms", "watch",
        f"{total} decorated dialogue tags. \"Said\" is invisible; "
        f"the alternatives draw attention to the author.",
        [f"{w} x{c}" for w, c in counts.most_common(8)],
        total,
    )


def check_impossible_tags(text: str) -> Optional[Finding]:
    """You cannot smile a sentence. These need a period, not a comma."""
    hits: List[str] = []
    pattern = re.compile(
        r"[,…]\s*[”\"]\s*(?:\w+\s+)?(" +
        "|".join(IMPOSSIBLE_TAGS) + r")\b",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text or ""):
        start = max(0, match.start() - 50)
        hits.append((text[start:match.end() + 10]).replace("\n", " ").strip())
    if not hits:
        return None
    return Finding(
        "impossible_tags", "flag",
        f"{len(hits)} action verbs used as speech tags. "
        f'Use a period: “I know.” She smiled. Not “I know,” she smiled.',
        hits[:5], len(hits),
    )


def check_dialogue_punctuation(text: str) -> List[Finding]:
    """US convention: commas and periods live inside the quotation marks."""
    findings: List[Finding] = []

    outside = re.findall(r"[a-z’']\s*[”\"]\s*,", text or "")
    if outside:
        findings.append(Finding(
            "punct_outside", "flag",
            f"{len(outside)} places where a comma sits outside the closing "
            f"quotation mark. US style puts it inside.",
            [o.strip() for o in outside[:5]], len(outside),
        ))

    # A capitalised speech tag after a comma: "...," She said.
    capitalised = re.findall(
        r",\s*[”\"]\s+(" + "|".join(
            v.capitalize() for v in DIALOGUE_TAG_VERBS
        ) + r")\b", text or ""
    )
    if capitalised:
        findings.append(Finding(
            "tag_capitalised", "flag",
            f"{len(capitalised)} speech tags capitalised after a comma. "
            f'“I know,” she said - lowercase, because the sentence continues.',
            list(dict.fromkeys(capitalised))[:5], len(capitalised),
        ))

    # Unbalanced quotation marks per paragraph.
    unbalanced = 0
    for para in paragraphs_of(text):
        opens = para.count("“")
        closes = para.count("”")
        straight = para.count('"')
        if opens != closes and straight % 2 != 0:
            unbalanced += 1
        elif not opens and not closes and straight % 2 != 0:
            unbalanced += 1
    if unbalanced:
        findings.append(Finding(
            "unbalanced_quotes", "watch",
            f"{unbalanced} paragraphs with an odd number of quotation marks. "
            f"Usually a missing close quote - though a speech continuing "
            f"across paragraphs is correct.",
            [], unbalanced,
        ))
    return findings


def check_sentence_rhythm(text: str) -> List[Finding]:
    sentences = sentences_of(text)
    if len(sentences) < 5:
        return []
    lengths = [len(words_of(s)) for s in sentences]
    mean = sum(lengths) / len(lengths)
    variance = sum((n - mean) ** 2 for n in lengths) / len(lengths)
    sd = variance ** 0.5

    findings: List[Finding] = []
    if sd < 4.5:
        findings.append(Finding(
            "rhythm", "watch",
            f"Sentence lengths are uniform (mean {mean:.0f} words, "
            f"variation {sd:.1f}). Monotonous rhythm reads as flat. "
            f"Break one in five into something very short.",
            [], 0,
        ))

    long_ones = [(i, n) for i, n in enumerate(lengths) if n > 45]
    if long_ones:
        findings.append(Finding(
            "long_sentences", "watch",
            f"{len(long_ones)} sentences over 45 words. These are the "
            f"\"sentence pretzels\" - grammatical but hard to follow.",
            [sentences[i][:100] + "..." for i, _n in long_ones[:3]],
            len(long_ones),
        ))

    # Runs of similar-length sentences.
    run = 1
    worst = 1
    for a, b in zip(lengths, lengths[1:]):
        if abs(a - b) <= 2:
            run += 1
            worst = max(worst, run)
        else:
            run = 1
    if worst >= 5:
        findings.append(Finding(
            "rhythm_run", "note",
            f"A run of {worst} consecutive sentences of near-identical length. "
            f"Vary one of them.",
            [], worst,
        ))
    return findings


def check_repetition(text: str, window: int = 45) -> List[Finding]:
    """Distinctive words repeated close together - the reader notices."""
    words = words_of(text)
    common = {
        "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at",
        "for", "with", "as", "by", "from", "that", "this", "it", "its",
        "he", "she", "they", "him", "her", "them", "his", "their", "i",
        "you", "we", "us", "me", "my", "was", "were", "is", "are", "be",
        "been", "had", "has", "have", "do", "did", "not", "no", "so", "if",
        "then", "than", "when", "what", "who", "would", "could", "said",
        "up", "out", "down", "back", "one", "all", "there", "would",
    }
    findings: List[Finding] = []
    echoes: Counter = Counter()
    positions: Dict[str, int] = {}
    for index, raw in enumerate(words):
        word = raw.lower()
        if word in common or len(word) < 5:
            continue
        previous = positions.get(word)
        if previous is not None and index - previous <= window:
            echoes[word] += 1
        positions[word] = index
    if echoes:
        findings.append(Finding(
            "echoes", "watch",
            f"{sum(echoes.values())} close repetitions of distinctive words "
            f"(within {window} words). Readers hear these even when they "
            f"cannot say why.",
            [f"{w} x{c}" for w, c in echoes.most_common(8)],
            sum(echoes.values()),
        ))

    # Paragraph openings.
    paras = paragraphs_of(text)
    if len(paras) >= 6:
        openers = Counter(
            (words_of(p)[:1] or [""])[0].lower() for p in paras
        )
        openers.pop("", None)
        repeated = [(w, c) for w, c in openers.most_common(4) if c >= 3]
        if repeated:
            findings.append(Finding(
                "para_openers", "note",
                "Several paragraphs open with the same word. Vary the entry "
                "point so the page does not look patterned.",
                [f"'{w}' starts {c} paragraphs" for w, c in repeated],
                sum(c for _w, c in repeated),
            ))

    # Sentence openings - the "I did, I went, I saw" trap.
    sentences = sentences_of(text)
    if len(sentences) >= 8:
        starts = Counter((words_of(s)[:1] or [""])[0].lower() for s in sentences)
        starts.pop("", None)
        worst = starts.most_common(1)[0] if starts else ("", 0)
        if worst[1] >= max(4, len(sentences) * 0.25):
            findings.append(Finding(
                "sentence_openers", "watch",
                f"{worst[1]} of {len(sentences)} sentences begin with "
                f"'{worst[0]}'. Restructure a few.",
                [], worst[1],
            ))
    return findings


def check_cliches(text: str) -> Optional[Finding]:
    lowered = (text or "").lower()
    hits = [phrase for phrase in CLICHES if phrase in lowered]
    if not hits:
        return None
    return Finding(
        "cliches", "watch",
        f"{len(hits)} stock phrases. Each was fresh once; a reader now "
        f"skims past them.",
        hits[:8], len(hits),
    )


def check_dialogue_ratio(text: str) -> Optional[Finding]:
    total = len(words_of(text))
    if total < 100:
        return None
    spoken = sum(len(words_of(m)) for m in DIALOGUE_RE.findall(text or ""))
    share = spoken / total * 100
    if share < 8:
        severity, note = "watch", (
            "Very little dialogue. Long narration stretches slow the pace and "
            "hide character."
        )
    elif share > 65:
        severity, note = "watch", (
            "Heavily dialogue-driven. Check the reader still knows where "
            "everyone is standing."
        )
    else:
        severity, note = "note", "A healthy balance for most commercial fiction."
    return Finding(
        "dialogue_ratio", severity,
        f"Dialogue is {share:.0f}% of the words. {note}",
        [], int(share),
    )


def check_mode_runs(text: str) -> Optional[Finding]:
    """
    The Rule of Two: more than two consecutive paragraphs in the same mode
    (all dialogue, all description, all interiority) flattens the texture.
    """
    paras = paragraphs_of(text)
    if len(paras) < 4:
        return None

    def mode(p: str) -> str:
        has_quote = bool(DIALOGUE_RE.search(p)) or p.lstrip().startswith(("“", '"'))
        if has_quote:
            return "dialogue"
        if re.search(r"\b(was|were|is|are|stood|sat|lay|hung)\b", p.lower()) \
                and len(words_of(p)) > 25:
            return "description"
        return "action"

    modes = [mode(p) for p in paras]
    worst_mode, worst_run = "", 0
    run, current = 1, modes[0]
    for m in modes[1:]:
        if m == current:
            run += 1
            if run > worst_run:
                worst_run, worst_mode = run, current
        else:
            run, current = 1, m
    if worst_run < 4:
        return None
    return Finding(
        "mode_runs", "note",
        f"{worst_run} consecutive {worst_mode} paragraphs. Interleaving "
        f"dialogue, action and description keeps the page varied.",
        [], worst_run,
    )


def check_readability(text: str) -> Optional[Finding]:
    sentences = sentences_of(text)
    words = words_of(text)
    if len(sentences) < 3 or len(words) < 50:
        return None
    syllables = sum(count_syllables(w) for w in words)
    words_per_sentence = len(words) / len(sentences)
    syllables_per_word = syllables / len(words)
    flesch = 206.835 - 1.015 * words_per_sentence - 84.6 * syllables_per_word
    grade = 0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59

    if flesch >= 70:
        band = "very easy - fits middle-grade and brisk commercial fiction"
    elif flesch >= 60:
        band = "plain and accessible - the sweet spot for most novels"
    elif flesch >= 50:
        band = "moderately dense - fine for literary and upmarket work"
    else:
        band = "dense - check this is a deliberate voice choice"

    return Finding(
        "readability", "note",
        f"Reading ease {flesch:.0f}, about grade {max(1, grade):.0f}. {band}. "
        f"Mean sentence {words_per_sentence:.1f} words.",
        [], int(flesch),
    )


def check_sensory_coverage(text: str) -> Optional[Finding]:
    """Which senses are on the page. Sight always wins; the others need help."""
    lowered = (text or "").lower()
    senses = {
        "sight": r"\b(saw|look|watch|glanc|stare|colour|color|bright|dark|"
                 r"shadow|gleam|glint|pale)\w*",
        "sound": r"\b(heard|hear|sound|listen|whisper|shout|creak|rustle|hum|"
                 r"silen|echo|clatter|thud)\w*",
        "smell": r"\b(smell|scent|odour|odor|reek|stank|stink|fragran|aroma|"
                 r"musty|perfume)\w*",
        "taste": r"\b(taste|tasted|bitter|sweet|sour|salt|metallic|tang)\w*",
        "touch": r"\b(felt|touch|rough|smooth|cold|warm|damp|dry|sticky|"
                 r"grip|brush|pressure|ache)\w*",
    }
    present = {
        name: len(re.findall(pattern, lowered))
        for name, pattern in senses.items()
    }
    missing = [name for name, count in present.items() if count == 0]
    if len(words_of(text)) < 200:
        return None
    if not missing:
        return Finding(
            "senses", "note",
            "All five senses appear. Good grounding.",
            [f"{k} {v}" for k, v in present.items()], 5,
        )
    return Finding(
        "senses", "note" if len(missing) <= 2 else "watch",
        f"Senses absent: {', '.join(missing)}. Smell and taste are the most "
        f"under-used and the fastest way to make a place feel real.",
        [f"{k} {v}" for k, v in present.items()], len(missing),
    )


def check_bracket_tags(text: str) -> Optional[Finding]:
    tags = re.findall(r"\[([^\]\n]{2,80})\]", text or "")
    tags = [t for t in tags if not t.lower().startswith("synopsis:")]
    if not tags:
        return None
    return Finding(
        "open_tags", "flag",
        f"{len(tags)} unresolved [bracket tags] still in the text.",
        tags[:8], len(tags),
    )


def check_double_spaces(text: str) -> Optional[Finding]:
    doubles = len(re.findall(r"\S  +\S", text or ""))
    repeated = re.findall(r"\b(\w+)\s+\1\b", (text or "").lower())
    problems = []
    count = 0
    if doubles:
        problems.append(f"{doubles} double spaces")
        count += doubles
    if repeated:
        problems.append(f"repeated words: {', '.join(sorted(set(repeated))[:6])}")
        count += len(repeated)
    if not problems:
        return None
    return Finding(
        "mechanics", "flag" if repeated else "note",
        "; ".join(problems).capitalize() + ".",
        [], count,
    )


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

CHECK_LABELS = {
    "open_tags": "Unresolved tags",
    "mechanics": "Mechanics",
    "impossible_tags": "Impossible speech tags",
    "punct_outside": "Quote punctuation",
    "tag_capitalised": "Tag capitalisation",
    "unbalanced_quotes": "Quotation marks",
    "adverbs": "Adverbs",
    "filler": "Filler words",
    "filter": "Filter words",
    "passive": "Passive voice",
    "said_bookisms": "Decorated tags",
    "cliches": "Stock phrases",
    "echoes": "Word echoes",
    "para_openers": "Paragraph openings",
    "sentence_openers": "Sentence openings",
    "rhythm": "Sentence rhythm",
    "long_sentences": "Long sentences",
    "rhythm_run": "Length runs",
    "dialogue_ratio": "Dialogue balance",
    "mode_runs": "Texture",
    "senses": "Sensory detail",
    "readability": "Readability",
}


def analyse(text: str) -> Report:
    """Run every check. Cheap enough for a whole novel."""
    report = Report(
        words=len(words_of(text)),
        sentences=len(sentences_of(text)),
        paragraphs=len(paragraphs_of(text)),
    )
    if not (text or "").strip():
        return report

    singles = [
        check_bracket_tags, check_double_spaces, check_impossible_tags,
        check_adverbs, check_filler, check_filter_words, check_passive,
        check_said_bookisms, check_cliches, check_dialogue_ratio,
        check_mode_runs, check_readability, check_sensory_coverage,
    ]
    for check in singles:
        try:
            finding = check(text)
        except Exception:
            continue
        if finding:
            report.findings.append(finding)

    multis = [check_dialogue_punctuation, check_sentence_rhythm, check_repetition]
    for check in multis:
        try:
            report.findings.extend(check(text) or [])
        except Exception:
            continue

    if report.sentences:
        report.metrics["words_per_sentence"] = round(
            report.words / report.sentences, 1
        )
    if report.paragraphs:
        report.metrics["words_per_paragraph"] = round(
            report.words / report.paragraphs, 1
        )
    return report


def report_text(report: Report, title: str = "") -> str:
    """Render a report for the diagnostics pane."""
    lines: List[str] = []
    if title:
        lines += [title, "=" * len(title), ""]
    lines.append(
        f"{report.words:,} words   {report.sentences:,} sentences   "
        f"{report.paragraphs:,} paragraphs"
    )
    if report.metrics.get("words_per_sentence"):
        lines.append(
            f"{report.metrics['words_per_sentence']} words per sentence, "
            f"{report.metrics.get('words_per_paragraph', 0)} per paragraph"
        )
    lines.append("")

    if not report.findings:
        lines.append("Nothing flagged. Either it is clean or it is very short.")
        return "\n".join(lines)

    for finding in report.by_severity():
        label = CHECK_LABELS.get(finding.check, finding.check)
        marker = {"flag": "!!", "watch": " ~", "note": "  "}.get(finding.severity, "  ")
        lines.append(f"{marker}  {label.upper()}")
        lines.append(f"      {finding.message}")
        if finding.examples:
            for example in finding.examples[:6]:
                lines.append(f"        - {example}")
        lines.append("")

    lines += [
        "-" * 58,
        "!! worth fixing    ~ worth a look    (blank) information only",
        "These are heuristics. Your voice beats every rule here.",
    ]
    return "\n".join(lines)


def scene_craft_check(scene) -> List[str]:
    """
    Developmental questions about a scene's *structure*, from its metadata.

    This is the Scene Quality Checker: it does not read the prose, it checks
    whether the scene is doing a scene's job.
    """
    issues: List[str] = []
    if not scene.synopsis:
        issues.append("No synopsis. If you cannot say what happens in a "
                      "sentence, the scene may not have a shape yet.")
    if scene.scene_type == "scene":
        if not scene.goal:
            issues.append("No goal: what does the POV character want here?")
        if not scene.conflict:
            issues.append("No conflict: what stands in the way?")
        if not scene.disaster:
            issues.append("No disaster: a scene that ends in clean success "
                          "releases tension instead of building it.")
    else:
        if not scene.reaction:
            issues.append("No reaction: let the character feel the last "
                          "disaster before they think.")
        if not scene.dilemma:
            issues.append("No dilemma: every option should be bad.")
        if not scene.decision:
            issues.append("No decision: the sequel exists to produce the "
                          "next scene's goal.")
    if not scene.pov_id:
        issues.append("No POV character assigned.")
    if scene.value_start and scene.value_end:
        if scene.value_start.strip().lower() == scene.value_end.strip().lower():
            issues.append("The emotional value does not change. If nothing "
                          "shifts, it is an episode, not a scene.")
    elif not scene.value_start and not scene.value_end:
        issues.append("No value shift recorded (what changes emotionally?).")
    if not scene.thread_ids:
        issues.append("Not linked to any plot thread.")
    if scene.word_count and scene.word_count < 200:
        issues.append(f"Only {scene.word_count} words - likely a fragment.")
    return issues
