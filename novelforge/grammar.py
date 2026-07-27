"""
Spelling and grammar, without a dictionary file.

A full English word list is a file this tool does not ship, so it cannot tell
you whether an arbitrary word exists. What it can do is catch the mistakes
people actually make, which is a much smaller and much better defined problem:

  * a curated list of the words English speakers reliably misspell
  * usage rules - its/it's, their/there, your/you're, could of, a/an
  * agreement - "he don't", "they was"
  * doubled words, spacing, and punctuation
  * the fantasy-specific one: a name that is close to a name in *your* book

That last one comes from lexicon.py and is the only part no other tool does.

Why not a real dictionary: Hunspell needs a C extension and a downloaded
dictionary; LanguageTool needs a Java runtime and about two hundred megabytes.
Both break the promise that this thing runs from a folder with nothing
installed. The rules below are pure Python and weigh nothing.

What this deliberately will not do is flag a word merely because it has not
seen it. In a fantasy manuscript most words it has not seen are correct, and a
checker that underlines Aethermoor four thousand times is a checker that gets
switched off in a week.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

# --------------------------------------------------------------------------
# Words English speakers reliably get wrong
# --------------------------------------------------------------------------
#
# Deliberately curated rather than generated: every entry is a real, common
# error with exactly one sensible correction. Anything ambiguous belongs in
# the rules below, where it can look at context.

MISSPELLINGS: Dict[str, str] = {
    "abondon": "abandon", "abbout": "about", "accomodate": "accommodate",
    "accomodation": "accommodation", "acheive": "achieve",
    "acheived": "achieved", "acknowlege": "acknowledge", "aquire": "acquire",
    "acquaintence": "acquaintance", "adress": "address", "adressed": "addressed",
    "advertisment": "advertisement", "agressive": "aggressive",
    "alledge": "allege", "allmost": "almost", "alot": "a lot",
    "allready": "already", "allright": "all right", "altho": "although",
    "amoung": "among", "anual": "annual", "apparant": "apparent",
    "appearence": "appearance", "arguement": "argument", "arithmatic": "arithmetic",
    "assasin": "assassin", "assasinate": "assassinate", "atleast": "at least",
    "attendence": "attendance", "audiance": "audience", "auxilary": "auxiliary",
    "basicly": "basically", "becuase": "because", "becomming": "becoming",
    "befor": "before", "begining": "beginning", "beleive": "believe",
    "beleived": "believed", "belive": "believe", "benifit": "benefit",
    "betwen": "between", "bizzare": "bizarre", "breif": "brief",
    "brilliantly": "brilliantly", "buisness": "business", "calender": "calendar",
    "camoflage": "camouflage", "carrer": "career", "catagory": "category",
    "cemetary": "cemetery", "changable": "changeable", "cheif": "chief",
    "collegue": "colleague", "collegues": "colleagues", "comming": "coming",
    "commited": "committed", "commitee": "committee", "comparision": "comparison",
    "completly": "completely", "concious": "conscious", "concieve": "conceive",
    "congradulate": "congratulate", "concensus": "consensus",
    "contraversy": "controversy", "conveniance": "convenience",
    "critisism": "criticism", "curiousity": "curiosity", "dacshund": "dachshund",
    "decieve": "deceive", "definately": "definitely", "definatly": "definitely",
    "definetly": "definitely", "desparate": "desperate", "diffrent": "different",
    "dilema": "dilemma", "disapear": "disappear", "disapoint": "disappoint",
    "disasterous": "disastrous", "dissapear": "disappear",
    "dissapoint": "disappoint", "doesnt": "doesn't", "dont": "don't",
    "drunkeness": "drunkenness", "embarass": "embarrass",
    "embarassed": "embarrassed", "embarassing": "embarrassing",
    "enviroment": "environment", "equiped": "equipped", "esspecially": "especially",
    "excede": "exceed", "excelent": "excellent", "excercise": "exercise",
    "exhilerate": "exhilarate", "existance": "existence", "expirience": "experience",
    "explaination": "explanation", "extreem": "extreme", "familar": "familiar",
    "fasinating": "fascinating", "febuary": "February", "fiery": "fiery",
    "finaly": "finally", "florescent": "fluorescent", "foriegn": "foreign",
    "forseeable": "foreseeable", "fourty": "forty", "foward": "forward",
    "freind": "friend", "freinds": "friends", "fullfil": "fulfil",
    "gaurd": "guard", "gaurantee": "guarantee", "generaly": "generally",
    "goverment": "government", "gracefull": "graceful", "grammer": "grammar",
    "greatfull": "grateful", "gratefull": "grateful", "greif": "grief",
    "harrass": "harass", "harrassment": "harassment", "happend": "happened",
    "heirarchy": "hierarchy", "heros": "heroes", "hipocrit": "hypocrite",
    "hopefull": "hopeful", "humourous": "humorous", "idae": "idea",
    "identicial": "identical", "ignorence": "ignorance", "imaginery": "imaginary",
    "immediatly": "immediately", "immidiately": "immediately",
    "incidently": "incidentally", "independant": "independent",
    "indispensible": "indispensable", "innoculate": "inoculate",
    "inteligent": "intelligent", "intresting": "interesting",
    "interupt": "interrupt", "irresistable": "irresistible", "jewelery": "jewellery",
    "knowlege": "knowledge", "labratory": "laboratory", "lenght": "length",
    "liason": "liaison", "libary": "library", "lightening": "lightning",
    "liesure": "leisure", "lonelyness": "loneliness", "maintainance": "maintenance",
    "maintenence": "maintenance", "managable": "manageable", "manoeuver": "manoeuvre",
    "marriege": "marriage", "medievel": "medieval", "millenium": "millennium",
    "miniscule": "minuscule", "mischevious": "mischievous", "mispell": "misspell",
    "misspelt": "misspelled", "momento": "memento", "morgage": "mortgage",
    "neccessary": "necessary", "necesary": "necessary", "negotiaton": "negotiation",
    "neice": "niece", "nieghbour": "neighbour", "noticable": "noticeable",
    "occassion": "occasion", "occured": "occurred", "occuring": "occurring",
    "occurance": "occurrence", "ommision": "omission", "oppurtunity": "opportunity",
    "orginal": "original", "outragous": "outrageous", "paralel": "parallel",
    "parliment": "parliament", "particulary": "particularly", "pasttime": "pastime",
    "peice": "piece", "percieve": "perceive", "perseverence": "perseverance",
    "personel": "personnel", "perswade": "persuade", "physicaly": "physically",
    "playright": "playwright", "pleasent": "pleasant", "posession": "possession",
    "possable": "possible", "potatoe": "potato", "practise": "practice",
    "prefered": "preferred", "prejudice": "prejudice", "presance": "presence",
    "priviledge": "privilege", "probaly": "probably", "proffesional": "professional",
    "promiss": "promise", "pronounciation": "pronunciation", "prufe": "proof",
    "psychadelic": "psychedelic", "publically": "publicly", "quarantee": "guarantee",
    "questionaire": "questionnaire", "readible": "readable", "realy": "really",
    "recieve": "receive", "recieved": "received", "recieving": "receiving",
    "reccomend": "recommend", "recomend": "recommend", "recomendation": "recommendation",
    "refered": "referred", "referance": "reference", "relevent": "relevant",
    "religous": "religious", "remeber": "remember", "reminise": "reminisce",
    "repitition": "repetition", "restarant": "restaurant", "rythm": "rhythm",
    "rhythem": "rhythm", "sacrifise": "sacrifice", "safty": "safety",
    "saftey": "safety", "sceduel": "schedule", "secratary": "secretary",
    "seperate": "separate", "seperated": "separated", "seperately": "separately",
    "sergent": "sergeant", "severly": "severely", "shedule": "schedule",
    "shreak": "shriek", "siege": "siege", "similer": "similar",
    "sincerly": "sincerely", "somthing": "something", "sophmore": "sophomore",
    "speach": "speech", "stoping": "stopping", "strenght": "strength",
    "strengh": "strength", "succesful": "successful", "succesfully": "successfully",
    "successfull": "successful", "suprise": "surprise", "suprised": "surprised",
    "surelly": "surely", "swiming": "swimming", "tatoo": "tattoo",
    "tendancy": "tendency", "therefor": "therefore", "threshhold": "threshold",
    "thier": "their", "tomatoe": "tomato", "tommorow": "tomorrow",
    "tommorrow": "tomorrow", "tounge": "tongue", "truely": "truly",
    "twelth": "twelfth", "tyrany": "tyranny", "underate": "underrate",
    "untill": "until", "unuseual": "unusual", "upholstry": "upholstery",
    "usualy": "usually", "vaccuum": "vacuum", "vegetarain": "vegetarian",
    "vehical": "vehicle", "visable": "visible", "wether": "whether",
    "wierd": "weird", "wellcome": "welcome", "whereever": "wherever",
    "wich": "which", "wief": "wife", "wilfull": "wilful", "withold": "withhold",
    "writting": "writing", "writen": "written", "yeild": "yield",
    "youre": "you're", "yourselfs": "yourselves", "teh": "the", "adn": "and",
    "taht": "that", "thsi": "this", "waht": "what", "hte": "the",
    "ot": "to", "fo": "of", "si": "is", "nad": "and",
}

# --------------------------------------------------------------------------
# Context rules
# --------------------------------------------------------------------------

#: (pattern, kind, message, replacement) - replacement may use \1 groups.
#: Written so that each one is either right or silent; a rule that fires on
#: correct prose is worse than no rule, because it teaches the writer to
#: ignore the panel.
_RULES: List[Tuple[str, str, str, Optional[str]]] = [
    # -- its / it's ------------------------------------------------------
    (r"\bits\s+(a|an|the|not|been|going|about|only|too|so|just|all|still|"
     r"raining|snowing|over|time|clear|true|possible|likely)\b",
     "usage", "\"its\" is possessive. Did you mean \"it's\" (it is)?",
     r"it's \1"),
    (r"\bit's\s+(own|way|edge|surface|weight|name|place|sake|head|tail|"
     r"colour|color|shape|value)\b",
     "usage", "\"it's\" means \"it is\". The possessive is \"its\".",
     r"its \1"),
    # -- their / there / they're -----------------------------------------
    (r"\btheir\s+(is|are|was|were|will\s+be)\b",
     "usage", "\"their\" is possessive. Did you mean \"there\"?",
     r"there \1"),
    (r"\bthere\s+(own|self|selves|father|mother|house|horses|swords|hands|"
     r"eyes|names|faces|voices)\b",
     "usage", "\"there\" is a place. Did you mean \"their\"?", r"their \1"),
    (r"\bthere\s+(going|coming|looking|standing|waiting|right|wrong)\b",
     "usage", "Did you mean \"they're\" (they are)?", r"they're \1"),
    # -- your / you're ---------------------------------------------------
    (r"\byour\s+(welcome|right|wrong|going|coming|not|the\s+one|a\s+)\b",
     "usage", "Did you mean \"you're\" (you are)?", None),
    (r"\byou're\s+(own|way|father|mother|horse|sword|name|hand)\b",
     "usage", "\"you're\" means \"you are\". The possessive is \"your\".",
     r"your \1"),
    # -- have / of -------------------------------------------------------
    (r"\b(could|should|would|must|might|may)\s+of\b",
     "grammar", "\"of\" should be \"have\" after a modal verb.",
     r"\1 have"),
    # -- agreement -------------------------------------------------------
    (r"\b(he|she|it|this|that)\s+don't\b",
     "grammar", "Should be \"doesn't\" with he, she or it.", r"\1 doesn't"),
    (r"\b(they|we|you|I)\s+doesn't\b",
     "grammar", "Should be \"don't\".", r"\1 don't"),
    (r"\b(they|we|you)\s+was\b",
     "grammar", "Should be \"were\".", r"\1 were"),
    (r"\b(he|she|it|I)\s+were\s+(?!to\b|it\b|I\b)",
     "grammar", "Should be \"was\" - unless this is deliberately subjunctive.",
     None),
    (r"\b(he|she|it)\s+have\b",
     "grammar", "Should be \"has\".", r"\1 has"),
    (r"\b(they|we|you)\s+has\b",
     "grammar", "Should be \"have\".", r"\1 have"),
    # -- than / then -----------------------------------------------------
    (r"\b(more|less|better|worse|greater|smaller|older|younger|rather|other|"
     r"fewer|larger|longer|shorter)\s+then\b",
     "usage", "Comparisons take \"than\", not \"then\".", None),
    # -- a / an ----------------------------------------------------------
    (r"\ba\s+(?=[aeiou])(?!(?:uni|use|user|usual|一|one\b|euro|ewe\b))(\w+)",
     "grammar", "\"a\" before a vowel sound is usually \"an\".", r"an \1"),
    (r"\ban\s+(?![aeiou]|hour|honest|honour|honor|heir)(\w+)",
     "grammar", "\"an\" before a consonant sound is usually \"a\".", r"a \1"),
    # -- doubled words ---------------------------------------------------
    (r"\b(\w+)\s+\1\b(?!\s+\1)",
     "typing", "This word is repeated.", r"\1"),
    # -- spacing and punctuation -----------------------------------------
    (r"\s+([,.;:!?])", "punctuation", "Space before punctuation.", r"\1"),
    (r"([,;:])(?=[^\s\"'\)\]])", "punctuation",
     "Missing space after punctuation.", r"\1 "),
    (r"  +", "punctuation", "More than one space.", " "),
    (r"\.\.\.\.+", "punctuation",
     "An ellipsis is three dots.", "..."),
    (r"[!?]{2,}", "punctuation",
     "One mark of punctuation is enough on the page.", None),
    # -- possessives -----------------------------------------------------
    (r"\bwhos\b", "usage", "Did you mean \"who's\" (who is) or \"whose\"?",
     None),
    (r"\blets\s+(go|see|say|have|get|find|make|try)\b",
     "usage", "Did you mean \"let's\" (let us)?", r"let's \1"),
    (r"\bcant\b", "usage", "Missing apostrophe: \"can't\".", "can't"),
    (r"\bwont\b", "usage", "Missing apostrophe: \"won't\".", "won't"),
    (r"\bwouldnt\b", "usage", "Missing apostrophe: \"wouldn't\".", "wouldn't"),
    (r"\bcouldnt\b", "usage", "Missing apostrophe: \"couldn't\".", "couldn't"),
    (r"\bshouldnt\b", "usage", "Missing apostrophe: \"shouldn't\".",
     "shouldn't"),
    (r"\bisnt\b", "usage", "Missing apostrophe: \"isn't\".", "isn't"),
    (r"\bwasnt\b", "usage", "Missing apostrophe: \"wasn't\".", "wasn't"),
    (r"\bhavent\b", "usage", "Missing apostrophe: \"haven't\".", "haven't"),
    (r"\bdidnt\b", "usage", "Missing apostrophe: \"didn't\".", "didn't"),
    (r"\bthats\b", "usage", "Missing apostrophe: \"that's\".", "that's"),
    (r"\bim\b(?=\s)", "usage", "Missing apostrophe: \"I'm\".", "I'm"),
    (r"\bive\b", "usage", "Missing apostrophe: \"I've\".", "I've"),
    (r"\bid\s+(rather|like|say|have|prefer)\b", "usage",
     "Missing apostrophe: \"I'd\".", r"I'd \1"),
]

_COMPILED = [
    (re.compile(pattern, re.IGNORECASE), kind, message, replacement)
    for pattern, kind, message, replacement in _RULES
]

_MISSPELL_PATTERN = re.compile(
    r"\b(" + "|".join(sorted(MISSPELLINGS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

#: Rules whose corrections are opinions rather than errors, kept separate so
#: they can be turned off without losing the real checks.
SOFT_KINDS = {"punctuation", "typing"}


@dataclass
class Hit:
    """One thing worth looking at, located precisely in the text."""

    start: int
    end: int
    kind: str            # spelling | usage | grammar | punctuation | typing | name
    text: str
    message: str
    suggestion: str = ""

    @property
    def severity(self) -> str:
        return "soft" if self.kind in SOFT_KINDS else "hard"


def _match_case(original: str, replacement: str) -> str:
    """Keep the writer's capitalisation when correcting a word."""
    if original.isupper() and len(original) > 1:
        return replacement.upper()
    if original[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement


def check(text: str, lexicon=None, limit: int = 300) -> List[Hit]:
    """
    Everything worth flagging in a passage.

    `lexicon` is the project's own vocabulary from lexicon.py. When it is
    given, two things change: words the writer has accepted are never
    questioned, and a capitalised phrase close to a name in the book is
    reported - which is the check no general tool can make.
    """
    if not text:
        return []
    hits: List[Hit] = []
    taken: List[Tuple[int, int]] = []

    def overlaps(start: int, end: int) -> bool:
        return any(start < b and a < end for a, b in taken)

    # -- known misspellings ------------------------------------------------
    for match in _MISSPELL_PATTERN.finditer(text):
        word = match.group(1)
        if lexicon is not None and lexicon.knows(word):
            continue        # the writer has claimed this word for their world
        correction = MISSPELLINGS[word.lower()]
        hits.append(Hit(match.start(), match.end(), "spelling", word,
                        f"\"{word}\" is a common misspelling.",
                        _match_case(word, correction)))
        taken.append((match.start(), match.end()))

    # -- context rules -----------------------------------------------------
    for pattern, kind, message, replacement in _COMPILED:
        for match in pattern.finditer(text):
            if overlaps(match.start(), match.end()):
                continue
            suggestion = ""
            if replacement:
                try:
                    suggestion = match.expand(replacement)
                except (re.error, IndexError):
                    suggestion = ""
            hits.append(Hit(match.start(), match.end(), kind, match.group(0),
                            message, suggestion))
            taken.append((match.start(), match.end()))
            if len(hits) > limit:
                break

    # -- names from this book ----------------------------------------------
    if lexicon is not None:
        for phrase, close in lexicon.suspicious(text):
            for match in re.finditer(re.escape(phrase), text):
                if overlaps(match.start(), match.end()):
                    continue
                hits.append(Hit(
                    match.start(), match.end(), "name", phrase,
                    f"\"{phrase}\" is not a name in this book.",
                    close[0] if close else ""))
                taken.append((match.start(), match.end()))
                break

    hits.sort(key=lambda h: h.start)
    return hits[:limit]


def summarise(hits: Sequence[Hit]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for hit in hits:
        counts[hit.kind] = counts.get(hit.kind, 0) + 1
    return counts


def report(hits: Sequence[Hit], text: str, title: str = "") -> str:
    """A readable list of what was found, with the line each one is on."""
    if not hits:
        return ("Nothing to report.\n\n"
                "No common misspellings, no usage or agreement mistakes, and "
                "every name matches the book.")

    def line_of(offset: int) -> int:
        return text.count("\n", 0, offset) + 1

    counts = summarise(hits)
    order = ["spelling", "grammar", "usage", "name", "typing", "punctuation"]
    labels = {
        "spelling": "SPELLING", "grammar": "GRAMMAR", "usage": "USAGE",
        "name": "NAMES FROM YOUR BOOK", "typing": "TYPING",
        "punctuation": "PUNCTUATION AND SPACING",
    }
    lines = [
        title or "WRITING CHECK",
        "=" * 64,
        "  ".join(f"{labels.get(k, k).title()}: {counts[k]}"
                  for k in order if k in counts),
        "",
    ]
    for kind in order:
        group = [h for h in hits if h.kind == kind]
        if not group:
            continue
        lines += ["-" * 64, labels.get(kind, kind.upper()), "-" * 64, ""]
        for hit in group:
            flat = " ".join(hit.text.split())
            lines.append(f"  line {line_of(hit.start):>4}   {flat}")
            lines.append(f"              {hit.message}")
            if hit.suggestion:
                lines.append(f"              suggested:  "
                             f"{' '.join(hit.suggestion.split())}")
            lines.append("")
    return "\n".join(lines)
