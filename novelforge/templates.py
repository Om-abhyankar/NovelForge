"""
Document templates - the actual field lists written into each Word file.

Every entity in a project gets a real .docx built from one of these. The field
sets are deliberately exhaustive: it is easier to delete a row in Word than to
realise six months in that you never recorded a character's core fear.

Each section is (heading, [(field_name, hint), ...]). Field names are the keys
used to read values back out, so renaming one orphans previously typed answers.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

Field = Tuple[str, str]
Section = Tuple[str, Sequence[Field]]


# ==========================================================================
# CHARACTER
# ==========================================================================

CHARACTER: List[Section] = [
    ("Identity", [
        ("Name", "As it appears in the manuscript"),
        ("Pronunciation", "If a reader could get it wrong"),
        ("Aliases & nicknames", "Who calls them what, and why"),
        ("Pronouns", ""),
        ("Age at story start", ""),
        ("Date of birth", "In-world calendar if you use one"),
        ("Birthplace", ""),
        ("Species / heritage", "If relevant to the world"),
        ("Occupation", "What they do for money and for meaning"),
        ("Social standing", "Class, caste, rank, reputation"),
    ]),
    ("Role in the Story", [
        ("Narrative role", "Protagonist / antagonist / mentor / foil / "
                           "love interest / ally / threshold guardian"),
        ("Is this a POV character?", "Yes / No"),
        ("First appearance", "Chapter and scene"),
        ("Last appearance", ""),
        ("Screen time", "Rough share of the book they occupy"),
        ("What the story does to them", "One sentence"),
    ]),
    ("The Arc", [
        ("Arc type", "Positive change / flat / disillusionment / fall / corruption"),
        ("The Ghost (the wound)", "The past event that taught them the Lie"),
        ("The Lie they believe", "The false claim about themselves or the world"),
        ("The Truth they need", "What would actually set them free"),
        ("The Want", "The concrete external goal they chase"),
        ("The Need", "The internal thing they actually require"),
        ("The Fatal Flaw", "How the Lie makes them act against themselves"),
        ("Characteristic moment", "The scene that shows who they are on page one"),
        ("State at the start", ""),
        ("Midpoint shift", "What they see differently halfway through"),
        ("State at the end", ""),
        ("The thing they would never do", "Until the climax makes them"),
        ("Cost of change", "What they must give up to grow"),
    ]),
    ("Psychology", [
        ("Enneagram type", "With wing, if you use it"),
        ("MBTI type", ""),
        ("Core fear", "What they organise their life around avoiding"),
        ("Core desire", ""),
        ("Shadow trait", "The disowned opposite of their public self - "
                         "the arc recovers this"),
        ("Defence mechanism", "Deflection, control, humour, withdrawal, "
                              "aggression, perfectionism"),
        ("Under stress they become", ""),
        ("Moral line they will not cross", ""),
        ("What they would die for", ""),
        ("What they would kill for", ""),
        ("Greatest shame", ""),
        ("Best memory", ""),
        ("How they see themselves", ""),
        ("How others see them", "The gap between these two is character"),
    ]),
    ("Voice & Speech", [
        ("Vocabulary and register", "Formal, blunt, ornate, clinical, regional"),
        ("Sentence rhythm", "Clipped / winding / fragmentary / balanced"),
        ("Verbal tics and catchphrases", "Use sparingly; one is plenty"),
        ("Profanity", "None, mild, constant, inventive"),
        ("Dialect or accent", "Suggest through word choice, not spelling"),
        ("How they deflect a hard question", ""),
        ("How they lie", "Over-explain, go quiet, change subject, "
                         "attack the asker"),
        ("Humour style", "Dry, cruel, self-deprecating, absent"),
        ("What they never talk about", ""),
        ("Sample line of dialogue", "A line only this character could say"),
    ]),
    ("Physical Presence", [
        ("Overall impression", "What a stranger notices in three seconds"),
        ("Height and build", ""),
        ("Hair", ""),
        ("Eyes", ""),
        ("Skin", ""),
        ("Distinguishing marks", "Scars, tattoos, missing fingers"),
        ("How they dress", "And what that choice signals"),
        ("Posture and movement", "How they enter a room"),
        ("Voice quality", "Pitch, volume, texture"),
        ("Health and disability", ""),
        ("Physical habit under pressure", "A tell the reader learns to read"),
    ]),
    ("Relationships", [
        ("Family", "Living, dead, estranged"),
        ("Closest ally", "And what that person needs from them"),
        ("Chief opponent", "Not necessarily the villain"),
        ("Love interest", ""),
        ("Mentor or authority", ""),
        ("Whom they have wronged", ""),
        ("Who has wronged them", ""),
        ("Secret relationship", "And who must never learn of it"),
        ("Whom they are pretending to be for", ""),
    ]),
    ("Background", [
        ("Childhood in one sentence", ""),
        ("Education", ""),
        ("Three formative events", ""),
        ("Places they have lived", ""),
        ("Career history", ""),
        ("Money", "How much, from where, and their relationship to it"),
        ("Faith or philosophy", ""),
        ("Politics", "Only if the story touches it"),
    ]),
    ("Competence & Texture", [
        ("Skills", "What they are genuinely good at"),
        ("Incompetence", "What they are badly wrong about"),
        ("Significant possessions", ""),
        ("Where they live", "And what the space says about them"),
        ("Daily routine", ""),
        ("Quirks and tells", ""),
        ("Hobbies and pleasures", ""),
        ("Pet peeves", ""),
        ("Sleep, food, vice", ""),
    ]),
    ("Secrets & Stakes", [
        ("Secrets they keep", ""),
        ("Who must never find out", ""),
        ("What they stand to lose", ""),
        ("What they are lying about to themselves", ""),
        ("Their worst-case outcome", ""),
    ]),
    ("Continuity Log", [
        ("Physical details established on the page", "Eye colour, age, scars - "
         "record them here the moment you commit"),
        ("Facts stated aloud in dialogue", ""),
        ("Timeline notes", "Ages at key events; do the arithmetic once"),
        ("Open questions", ""),
    ]),
]


# ==========================================================================
# LOCATION
# ==========================================================================

LOCATION: List[Section] = [
    ("Identity", [
        ("Name", ""),
        ("Also known as", ""),
        ("Type", "City, house, ship, forest, station, realm"),
        ("Contained within", "Parent region, nation or world"),
        ("Position", "Coordinates, or 'three days north of the capital'"),
        ("First appearance", ""),
    ]),
    ("Geography & Structure", [
        ("Terrain", ""),
        ("Size and scale", "Give the reader something to measure against"),
        ("Climate", ""),
        ("Season during the story", ""),
        ("Weather that matters", ""),
        ("Landmarks", ""),
        ("Layout and architecture", ""),
        ("Ways in and out", "Doors, roads, passes, airlocks - escape routes "
                            "are plot"),
        ("Travel times to other places", ""),
    ]),
    ("The Five Senses", [
        ("Sight", "Light quality, colour, what dominates the eye"),
        ("Sound", "Constant background and sudden intrusions"),
        ("Smell", "The single most underused sense - be specific"),
        ("Taste", "Air, water, food, dust"),
        ("Touch and temperature", "Underfoot, on the skin, in the throat"),
        ("Overall atmosphere", "One phrase you can return to"),
    ]),
    ("Inhabitants", [
        ("Population", ""),
        ("Who lives here", ""),
        ("Who holds power", ""),
        ("Social structure", ""),
        ("Languages spoken", ""),
        ("How strangers are treated", ""),
        ("Where people gather", ""),
    ]),
    ("Culture & Systems", [
        ("Economy", "What is made, traded, or extracted"),
        ("Laws and enforcement", ""),
        ("Customs and manners", ""),
        ("Taboos", ""),
        ("Religion and ritual", ""),
        ("Food and drink", ""),
        ("Dress", ""),
        ("Festivals and holidays", ""),
    ]),
    ("History", [
        ("Founded or formed", ""),
        ("Defining historical events", ""),
        ("Ruins and remains", ""),
        ("Reputation elsewhere", ""),
        ("Local legends", ""),
    ]),
    ("Story Function", [
        ("Why this scene happens here", "If it could happen anywhere, "
                                        "the setting is doing no work"),
        ("Mood it creates", ""),
        ("What it reveals about character", ""),
        ("Obstacles it presents", ""),
        ("How it changes across the book", ""),
        ("Scenes set here", ""),
    ]),
    ("Continuity Log", [
        ("Details established on the page", ""),
        ("Map notes", ""),
        ("Distances committed to", ""),
    ]),
]


# ==========================================================================
# ITEM / OBJECT
# ==========================================================================

ITEM: List[Section] = [
    ("Identity", [
        ("Name", ""),
        ("Type", "Weapon, heirloom, document, artefact, technology, key"),
        ("Current owner", ""),
        ("Current location", ""),
        ("First appearance", ""),
    ]),
    ("Physical", [
        ("Appearance", ""),
        ("Size and weight", "Can one person carry it? This is plot-relevant"),
        ("Material", ""),
        ("Age and condition", ""),
        ("Markings or inscriptions", ""),
        ("How it feels to hold", ""),
        ("Sound or smell", ""),
    ]),
    ("Function & Rules", [
        ("What it does", ""),
        ("Rules governing it", "Be strict; consistency is what makes it real"),
        ("Cost of use", "Every power needs a price"),
        ("Limits and failure modes", ""),
        ("How it is activated", ""),
        ("Who can use it", ""),
        ("What it cannot do", "Write this down or you will cheat later"),
    ]),
    ("History", [
        ("Origin", ""),
        ("Maker", ""),
        ("Previous owners", ""),
        ("How the current owner got it", ""),
        ("Legends attached to it", ""),
    ]),
    ("Story Function", [
        ("Role in the plot", ""),
        ("What it symbolises", ""),
        ("Who else wants it", ""),
        ("What happens if it is lost or destroyed", ""),
        ("Where it ends up", ""),
    ]),
]


# ==========================================================================
# FACTION / ORGANISATION
# ==========================================================================

FACTION: List[Section] = [
    ("Identity", [
        ("Name", ""),
        ("Also known as", "Including what enemies call them"),
        ("Type", "Government, guild, cult, corporation, family, crew, army"),
        ("Founded", ""),
        ("Base of operations", ""),
        ("Size", ""),
        ("Symbol, colours, motto", ""),
    ]),
    ("Structure", [
        ("Leader", ""),
        ("How power is held", "Inherited, elected, seized, earned"),
        ("Ranks and titles", ""),
        ("How you join", ""),
        ("How you leave", "If you can"),
        ("Internal factions", "Every organisation contains its own opposition"),
        ("Who really decides things", ""),
    ]),
    ("Purpose", [
        ("Stated goal", ""),
        ("Actual goal", ""),
        ("Methods", ""),
        ("Resources", ""),
        ("Funding", ""),
        ("Territory or reach", ""),
    ]),
    ("Ideology", [
        ("Core beliefs", ""),
        ("Rituals", ""),
        ("Taboos", ""),
        ("The recruitment pitch", "Write it persuasively - it should work"),
        ("What they would never do", ""),
        ("How they justify their worst act", ""),
    ]),
    ("Relationships", [
        ("Allies", ""),
        ("Enemies", ""),
        ("Uneasy neutrals", ""),
        ("Secret ties", ""),
    ]),
    ("Weaknesses", [
        ("Structural weakness", ""),
        ("Internal fracture line", ""),
        ("What would destroy them", ""),
    ]),
    ("Story Function", [
        ("Role in the plot", ""),
        ("Members who appear on the page", ""),
        ("First appearance", ""),
        ("Their arc across the book", ""),
    ]),
]


# ==========================================================================
# PLOT THREAD
# ==========================================================================

PLOT_THREAD: List[Section] = [
    ("Identity", [
        ("Thread name", ""),
        ("Type", "A story (main plot) / B story (relationship) / subplot / "
                 "thematic thread"),
        ("Priority", "Primary, secondary, minor"),
        ("Characters involved", ""),
    ]),
    ("The Dramatic Question", [
        ("The question this thread asks", "Phrase it so the answer is yes or no"),
        ("The answer", ""),
        ("Theme it carries", ""),
        ("Why the reader should care", ""),
    ]),
    ("Arc", [
        ("Where it is set up", "Chapter and scene"),
        ("Escalation points", "One per act at minimum"),
        ("Where it peaks", ""),
        ("How it resolves", ""),
        ("The payoff", "What the reader gets for following it"),
        ("Is it resolved or deliberately left open?", ""),
    ]),
    ("Planting & Payoff", [
        ("What is planted", ""),
        ("Where it is planted", "Plant it at least two scenes before it matters"),
        ("Where it pays off", ""),
        ("Is the plant subtle enough?", ""),
        ("Is the payoff earned?", ""),
    ]),
    ("Tracking", [
        ("Scenes in this thread", ""),
        ("Longest gap between appearances", "A thread absent for 100 pages "
                                            "reads as abandoned"),
        ("Status", "Planned / in progress / drafted / resolved / cut"),
        ("Open loose ends", ""),
    ]),
]


# ==========================================================================
# WORLD BIBLE - one document per system
# ==========================================================================

WORLD_MAGIC: List[Section] = [
    ("The System", [
        ("Name of the system", ""),
        ("Hard or soft?", "Hard = reader knows the rules and can predict "
                          "outcomes. Soft = mystery preserved. Pick one."),
        ("One-sentence summary", ""),
        ("Source of power", ""),
    ]),
    ("Rules", [
        ("What it can do", ""),
        ("What it absolutely cannot do", "The most important row on this page"),
        ("The cost", "Physical, mental, moral, material"),
        ("Limits", "Range, duration, frequency, materials required"),
        ("How it is learned", ""),
        ("Who can use it", "And who cannot, and why"),
        ("How it fails", ""),
        ("What happens when it is misused", ""),
    ]),
    ("Society", [
        ("Who controls access", ""),
        ("Legal status", ""),
        ("Public attitude", "Feared, revered, regulated, hidden"),
        ("Economic effect", "If it can make food or gold, the economy is "
                            "not medieval"),
        ("Military effect", ""),
        ("Effect on medicine and death", ""),
    ]),
    ("Story Use", [
        ("How it creates problems", "A power that only solves problems is "
                                    "not a story engine"),
        ("How the protagonist's relationship to it changes", ""),
        ("The rule that gets broken at the climax", ""),
        ("Consistency check log", "Every on-page use, so you never contradict"),
    ]),
]

WORLD_POLITICS: List[Section] = [
    ("Power Map", [
        ("Who rules", ""),
        ("How they took power", ""),
        ("How power passes on", ""),
        ("Who actually holds power", "Often not the same answer"),
        ("Rival powers", ""),
        ("Current tensions", ""),
    ]),
    ("Governance", [
        ("Form of government", ""),
        ("Laws that matter to the plot", ""),
        ("Justice and punishment", ""),
        ("Taxation", ""),
        ("Military and policing", ""),
        ("Bureaucracy", "Where a character could get stuck"),
    ]),
    ("Society", [
        ("Class structure", ""),
        ("Social mobility", ""),
        ("Who is excluded and how", ""),
        ("Marriage, family, inheritance", ""),
        ("Education", ""),
        ("Attitudes to outsiders", ""),
    ]),
    ("Conflict", [
        ("Recent wars", ""),
        ("Simmering grievances", ""),
        ("What would start a war", ""),
        ("Who profits from unrest", ""),
    ]),
]

WORLD_RELIGION: List[Section] = [
    ("Belief", [
        ("Name of the faith", ""),
        ("Deities or forces", ""),
        ("Creation story", ""),
        ("What happens after death", ""),
        ("Core moral teaching", ""),
        ("Sacred text or oral tradition", ""),
    ]),
    ("Practice", [
        ("Rituals", ""),
        ("Holy days", ""),
        ("Places of worship", ""),
        ("Clergy and hierarchy", ""),
        ("Prayers, oaths and curses", "These leak into everyday dialogue"),
        ("Dietary and dress rules", ""),
        ("Rites of passage", "Birth, adulthood, marriage, death"),
    ]),
    ("Power & Conflict", [
        ("Relationship to the state", ""),
        ("Heresies and schisms", ""),
        ("Rival faiths", ""),
        ("How non-believers are treated", ""),
        ("What the faith gets wrong", ""),
    ]),
]

WORLD_CULTURE: List[Section] = [
    ("Daily Life", [
        ("What people eat", ""),
        ("What people wear", ""),
        ("Housing", ""),
        ("Work and the working day", ""),
        ("Entertainment", ""),
        ("Music and art", ""),
        ("Sport and games", ""),
    ]),
    ("Manners", [
        ("How strangers greet each other", ""),
        ("Signs of respect and insult", ""),
        ("Table manners", ""),
        ("Gift customs", ""),
        ("Taboos", ""),
        ("What is considered obscene", ""),
    ]),
    ("Language", [
        ("Languages and who speaks them", ""),
        ("Naming conventions", "Given names, family names, patronymics"),
        ("Honorifics and titles", ""),
        ("Common idioms and oaths", "Invent three; they do enormous work"),
        ("Slang by class or region", ""),
        ("Untranslatable words", ""),
    ]),
    ("Invented Terms Glossary", [
        ("Term / spelling / meaning", "One per line. Lock the spelling now, "
         "and check the manuscript against this list before you submit."),
    ]),
]

WORLD_TECH: List[Section] = [
    ("Level & Reach", [
        ("Overall technology level", ""),
        ("Most advanced thing that exists", ""),
        ("Who has access", ""),
        ("What is deliberately absent", "And why nobody invented it"),
    ]),
    ("Infrastructure", [
        ("Transport", "This sets the pace of your entire plot"),
        ("Communication", "How fast can bad news travel?"),
        ("Energy", ""),
        ("Medicine", "What is survivable determines your stakes"),
        ("Weapons", ""),
        ("Information storage", ""),
        ("Sanitation and water", ""),
    ]),
    ("Economy", [
        ("Currency", ""),
        ("What a labourer earns per day", "Your price anchor for everything"),
        ("Cost of bread, a bed, a horse, a passage", ""),
        ("Main industries", ""),
        ("Trade routes and goods", ""),
        ("Banking, debt and credit", ""),
        ("Who is poor and why", ""),
    ]),
]

WORLD_CALENDAR: List[Section] = [
    ("Timekeeping", [
        ("Name of the calendar", ""),
        ("Days in a year", ""),
        ("Months and their names", ""),
        ("Days in a week and their names", ""),
        ("How years are counted", "From what event?"),
        ("Current year in the story", ""),
        ("Moons and cycles", ""),
        ("Seasons", ""),
        ("How time of day is told", ""),
    ]),
    ("Observances", [
        ("Major festivals and dates", ""),
        ("Days of ill omen", ""),
        ("Agricultural cycle", ""),
    ]),
    ("Conversion", [
        ("In-world date to story day", "Keep a conversion note so the "
         "Timeline and the manuscript never disagree"),
    ]),
]

WORLD_NATURE: List[Section] = [
    ("Geography", [
        ("Continents and regions", ""),
        ("Major water", ""),
        ("Mountains and barriers", ""),
        ("Climate zones", ""),
        ("Natural hazards", ""),
    ]),
    ("Life", [
        ("Notable flora", ""),
        ("Notable fauna", ""),
        ("Domesticated animals", ""),
        ("Dangerous creatures", ""),
        ("Invented species and their ecology", "What does it eat? "
         "An animal without a food source is a prop"),
        ("Diseases", ""),
    ]),
]

WORLD_HISTORY: List[Section] = [
    ("Deep History", [
        ("Founding myth", ""),
        ("Ages or epochs", ""),
        ("The event everyone still talks about", ""),
        ("Lost civilisations", ""),
    ]),
    ("Recent History", [
        ("Last fifty years", ""),
        ("Last five years", ""),
        ("What the older generation remembers that the young do not", ""),
        ("How history is taught versus what happened", ""),
    ]),
]

WORLD_BIBLE_DOCS: Dict[str, Tuple[str, str, List[Section]]] = {
    # filename stem: (title, subtitle, sections)
    "Magic or Power System": (
        "Magic or Power System",
        "Rules, costs and limits. Skip if your world has none.",
        WORLD_MAGIC,
    ),
    "Politics & Power": (
        "Politics & Power",
        "Who rules, who resents it, and what would break it",
        WORLD_POLITICS,
    ),
    "Religion & Belief": (
        "Religion & Belief",
        "Faith, ritual and the oaths people swear",
        WORLD_RELIGION,
    ),
    "Culture & Language": (
        "Culture & Language",
        "Daily life, manners and invented vocabulary",
        WORLD_CULTURE,
    ),
    "Technology & Economy": (
        "Technology & Economy",
        "What exists, who can afford it, and what a day's work buys",
        WORLD_TECH,
    ),
    "Calendar & Timekeeping": (
        "Calendar & Timekeeping",
        "Days, months, seasons and how years are counted",
        WORLD_CALENDAR,
    ),
    "Geography & Nature": (
        "Geography & Nature",
        "Land, weather, flora and fauna",
        WORLD_NATURE,
    ),
    "History & Timeline": (
        "History & Timeline",
        "Deep past and living memory",
        WORLD_HISTORY,
    ),
}


# ==========================================================================
# PROJECT-LEVEL PLANNING DOCUMENTS
# ==========================================================================

PREMISE: List[Section] = [
    ("The One Sentence", [
        ("Logline", "Fifteen words or fewer. Use roles, not names: "
                    "'A grieving locksmith must...'"),
        ("Genre and comparable titles", "X meets Y, for readers of Z"),
        ("Target word count", ""),
        ("Point of view and tense", "First / third limited / third omniscient; "
                                    "past / present"),
    ]),
    ("The Paragraph", [
        ("Setup", "Who, where, and what is unsatisfying"),
        ("Disaster one", "Roughly the 25% mark"),
        ("Disaster two", "The midpoint"),
        ("Disaster three", "The 75% low point"),
        ("Ending", "How it resolves - write it now, change it later"),
    ]),
    ("Foundations", [
        ("Protagonist's want", ""),
        ("Protagonist's need", ""),
        ("Central conflict", ""),
        ("Antagonistic force", "A person, a system, a flaw, or nature"),
        ("The stakes", "What is lost if they fail"),
        ("Why now?", "Why does this story start today and not a year ago"),
        ("Theme", "Phrase as an argument, not a topic: not 'grief' but "
                  "'grief shared is survivable'"),
        ("The question the book asks", ""),
        ("The answer the book gives", ""),
    ]),
    ("Promise to the Reader", [
        ("The promise of the premise", "What experience are you selling?"),
        ("The scene readers will remember", ""),
        ("Why you are the person to write this", ""),
    ]),
]

WHY_COMPASS: List[Section] = [
    ("Why This Story", [
        ("Why am I telling this story?", "Write it long. Come back on the "
         "bad days and read it."),
        ("What do I want a reader to feel?", ""),
        ("What am I trying to work out by writing it?", ""),
        ("Whom is it for?", "One specific person, real or imagined"),
        ("What would it cost me to abandon it?", ""),
    ]),
    ("When It Gets Hard", [
        ("The last time writing felt good, it was because", ""),
        ("Evidence I can actually do this", "List finished things, however small"),
        ("What 'finished' looks like", "Define it so you can recognise it"),
        ("What I will do instead of quitting", ""),
    ]),
]

SERIES_CONTINUITY: List[Section] = [
    ("Established Facts", [
        ("Character ages and birth years", "Do the arithmetic once, here"),
        ("Physical descriptions committed to", ""),
        ("Place names and spellings", ""),
        ("Invented terms and spellings", ""),
        ("Distances and travel times", ""),
        ("Money and prices", ""),
        ("Dates and the story calendar", ""),
    ]),
    ("Running Threads", [
        ("Unresolved questions", ""),
        ("Promises made to the reader", ""),
        ("Foreshadowing planted, not yet paid", ""),
        ("Characters last seen where", ""),
        ("Objects last seen where", ""),
    ]),
    ("Voice & Texture", [
        ("Recurring images and motifs", ""),
        ("Running jokes", ""),
        ("Chapter and section conventions", "Numbered? Titled? POV headers?"),
        ("Style decisions", "Serial comma, spelling variant, number style"),
    ]),
    ("Corrections", [
        ("Errors found after publication", "So book two does not repeat them"),
        ("Retcons and how they are justified", ""),
    ]),
]

QUERY_LETTER: List[Section] = [
    ("The Hook", [
        ("Personalisation", "Why this agent specifically - one honest line"),
        ("Title", ""),
        ("Word count", "Rounded to the nearest thousand"),
        ("Genre and category", ""),
        ("Comparable titles", "Two, published in the last five years, "
                              "not bestsellers"),
        ("The hook sentence", "Your logline, sharpened"),
    ]),
    ("The Book", [
        ("Paragraph one - protagonist and world", "Who, where, what they want"),
        ("Paragraph two - the inciting complication", "What goes wrong and "
                                                      "what they must now do"),
        ("Paragraph three - stakes and the choice", "End on the dilemma, "
         "not on 'will they succeed?'"),
        ("Do not include", "The ending, subplots, more than three named "
                           "characters, rhetorical questions"),
    ]),
    ("The Cook", [
        ("Publication credits", "If any; omit gracefully if none"),
        ("Relevant expertise", "Why you can write this authentically"),
        ("Professional affiliations", ""),
        ("One human line", "Something memorable and brief"),
        ("Closing", "Thanks, and what is attached"),
    ]),
    ("Checklist", [
        ("Under 350 words?", ""),
        ("Agent's name spelled correctly?", ""),
        ("Submission guidelines followed exactly?", ""),
        ("No typos in the first sentence?", ""),
        ("Read aloud once?", ""),
    ]),
]

SYNOPSIS_SHEET: List[Section] = [
    ("Setup", [
        ("Opening situation", ""),
        ("Protagonist introduced", "Name in caps on first mention"),
        ("Inciting incident", ""),
        ("What they decide to do", ""),
    ]),
    ("Middle", [
        ("First major complication", ""),
        ("Rising obstacles", ""),
        ("The midpoint turn", ""),
        ("What goes wrong", ""),
        ("The low point", ""),
    ]),
    ("End", [
        ("The final push", ""),
        ("The climax", "Say exactly what happens - a synopsis spoils "
                       "the ending on purpose"),
        ("The resolution", ""),
        ("Where everyone ends up", ""),
    ]),
    ("Craft Notes", [
        ("Present tense, third person", "Even if the novel is first-person past"),
        ("Length", "One page single-spaced, or as the agent asks"),
        ("Emotional throughline", "Not just events - what it costs them"),
    ]),
]

BETA_QUESTIONNAIRE: List[Section] = [
    ("Reader", [
        ("Name", ""),
        ("What do you usually read?", ""),
        ("Date sent", ""),
        ("Date returned", ""),
    ]),
    ("The Four Questions", [
        ("What was great?", "So I do not cut it in revision"),
        ("Where were you bored?", "Be specific - name the page or chapter "
                                  "where you started skimming"),
        ("What confused you?", "Where did you have to reread?"),
        ("What did not you believe?", "Where did a character act "
                                      "out of character?"),
    ]),
    ("Specifics", [
        ("Did you stop reading anywhere? Where and why?", ""),
        ("Which character did you care about most? Least?", ""),
        ("Did you guess the ending? When?", ""),
        ("Was anything unclear about the world or its rules?", ""),
        ("Did the ending satisfy you?", ""),
        ("Would you recommend it? To whom?", ""),
        ("Anything you want to say that I did not ask about?", ""),
    ]),
]

SCENE_CARD: List[Section] = [
    ("Card", [
        ("Scene title", ""),
        ("POV character", ""),
        ("Location", ""),
        ("Story date and time", ""),
        ("Who is present", ""),
        ("Synopsis", "One or two sentences - this is the index card"),
    ]),
    ("Scene (Goal / Conflict / Disaster)", [
        ("Goal", "What the POV character wants in this scene, concretely"),
        ("Conflict", "Who or what opposes it"),
        ("Disaster", "How it goes wrong. Yes-but or no-and-furthermore"),
    ]),
    ("Sequel (Reaction / Dilemma / Decision)", [
        ("Reaction", "The emotional aftermath"),
        ("Dilemma", "Every option is bad"),
        ("Decision", "The choice that becomes the next scene's goal"),
    ]),
    ("Value Shift", [
        ("Emotional value at the start", "e.g. hopeful, safe, trusting"),
        ("Emotional value at the end", "It must be different, or the scene "
                                       "is not a scene"),
        ("What the reader learns", ""),
        ("What changes irreversibly", ""),
    ]),
    ("Craft Check", [
        ("Is the goal clear in the first 15%?", ""),
        ("Does the character change tactics under pressure?", ""),
        ("Does the ending raise a new question?", ""),
        ("Which plot threads does this advance?", ""),
        ("Which senses are on the page?", ""),
    ]),
]

DIALOGUE_RULES = [
    ("New paragraph per speaker",
     "Every change of speaker starts a new indented paragraph. No exceptions."),
    ("Punctuation inside the quotes",
     'US convention: commas and periods go inside. "I know," she said. '
     'Not "I know", she said.'),
    ("Lowercase tags after a comma",
     '"I know," she said. Not "I know," She said. The tag continues '
     'the sentence.'),
    ("Period when the tag is an action",
     'She crossed the room. "I know." An action is not a speech tag - '
     'you cannot smile a sentence.'),
    ("Em dash interrupts, ellipsis trails off",
     '"But I thought you-" / "I never said that." versus '
     '"I just thought maybe..."'),
    ("Single quotes nest inside double",
     'She said, "He told me \'never again\' and I believed him."'),
    ("Split a long speech at a paragraph break",
     "Open quotes on each new paragraph; close only at the very end "
     "of the speech."),
    ("Said is invisible - use it",
     "Avoid said-bookisms: expostulated, ejaculated, chortled. "
     "Said and asked disappear; the alternatives shout."),
    ("Cut the greetings",
     "Real dialogue on the page starts after hello and ends before goodbye."),
    ("No 'As you know, Bob'",
     "Characters must not explain to each other things they both already "
     "know for the reader's benefit."),
]


# ==========================================================================
# Registry for entity types
# ==========================================================================

ENTITY_TEMPLATES: Dict[str, Tuple[str, List[Section]]] = {
    "character": ("CHARACTER", CHARACTER),
    "location": ("LOCATION", LOCATION),
    "item": ("ITEM", ITEM),
    "faction": ("FACTION", FACTION),
    "thread": ("PLOT THREAD", PLOT_THREAD),
}


def sections_for(entity_type: str) -> List[Section]:
    return ENTITY_TEMPLATES.get(entity_type, ("", []))[1]


def kicker_for(entity_type: str) -> str:
    return ENTITY_TEMPLATES.get(entity_type, ("", []))[0]


def field_names(sections: Sequence[Section]) -> List[str]:
    """Flat list of every field name in a template, for validation."""
    return [name for _heading, fields in sections for name, _hint in fields]
