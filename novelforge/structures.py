"""
Narrative structure frameworks, as data.

Each framework is a list of beats. `pct` is the beat's position expressed as a
fraction of total manuscript length, which lets the tool convert a target word
count into a target word position for every beat ("your midpoint should land
around word 45,000").

`pct` may be None for frameworks that describe a process rather than a
position (the Snowflake Method) or where the source gives no fixed placement.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional


class Beat(NamedTuple):
    key: str
    name: str
    pct: Optional[float]  # 0.0 - 1.0, or None if unplaced
    prompt: str           # the question this beat asks the writer


class Framework(NamedTuple):
    key: str
    name: str
    source: str
    note: str
    beats: List[Beat]


# --------------------------------------------------------------------------
# Three-Act Structure with K.M. Weiland's percentage markers
# --------------------------------------------------------------------------

THREE_ACT = Framework(
    key="three_act",
    name="Three-Act Structure",
    source="K.M. Weiland, Structuring Your Novel",
    note=(
        "The workhorse. Percentages are Weiland's markers; treat them as "
        "gravitational centres, not deadlines."
    ),
    beats=[
        Beat("hook", "The Hook", 0.01,
             "What question, danger or intrigue makes page one unputdownable?"),
        Beat("setup", "Setup", 0.03,
             "Show the normal world and what is unsatisfying about it."),
        Beat("inciting", "Inciting Event", 0.12,
             "What brushes against the protagonist and disturbs the status quo? "
             "They can still walk away at this point."),
        Beat("plot_point_1", "First Plot Point", 0.25,
             "The door closes. What makes it impossible to return to the "
             "normal world? This ends Act One."),
        Beat("reaction", "Reaction / New World", 0.30,
             "How does the protagonist flounder in unfamiliar territory?"),
        Beat("pinch_1", "First Pinch Point", 0.37,
             "Remind the reader of the antagonistic force. Show its power "
             "directly, not through the protagonist's guesses."),
        Beat("midpoint", "Midpoint / Second Plot Point", 0.50,
             "The moment of revelation that flips the protagonist from "
             "reaction to action. What do they finally understand?"),
        Beat("pinch_2", "Second Pinch Point", 0.62,
             "The antagonist strikes again, harder. The cost is now personal."),
        Beat("plot_point_3", "Third Plot Point", 0.75,
             "The low moment. A brush with death - literal, professional or "
             "spiritual. The lie the character believes must die here."),
        Beat("act_three", "Renewed Push", 0.80,
             "Armed with the truth, what plan do they form?"),
        Beat("climax", "Climax Begins", 0.88,
             "The final confrontation opens. No more delay."),
        Beat("climactic_moment", "Climactic Moment", 0.98,
             "The single instant the story's central question is answered."),
        Beat("resolution", "Resolution", 0.99,
             "Show the new normal. Prove the change is real."),
    ],
)

# --------------------------------------------------------------------------
# Save the Cat! - Blake Snyder's 15 beats
# --------------------------------------------------------------------------

SAVE_THE_CAT = Framework(
    key="save_the_cat",
    name="Save the Cat! Beat Sheet",
    source="Blake Snyder, Save the Cat!",
    note=(
        "Fifteen beats, originally page numbers for a 110-page screenplay, "
        "here converted to manuscript percentages."
    ),
    beats=[
        Beat("opening_image", "Opening Image", 0.01,
             "A single image that sets tone and shows the 'before' state."),
        Beat("theme_stated", "Theme Stated", 0.05,
             "Someone states the story's thematic argument - usually to a "
             "protagonist who is not ready to hear it."),
        Beat("setup", "Set-Up", 0.08,
             "The status quo, the flaw, and the six things that need fixing."),
        Beat("catalyst", "Catalyst", 0.10,
             "The life-changing telegram. The world knocks."),
        Beat("debate", "Debate", 0.15,
             "Should I go? The protagonist's last chance to refuse."),
        Beat("break_into_two", "Break Into Two", 0.20,
             "They choose. Act Two is a different world with different rules."),
        Beat("b_story", "B Story", 0.22,
             "The subplot - usually the relationship that carries the theme."),
        Beat("fun_and_games", "Fun and Games", 0.30,
             "The promise of the premise. Why the reader picked up this book."),
        Beat("midpoint", "Midpoint", 0.50,
             "A false victory or false defeat. Stakes are raised and the "
             "clock starts ticking."),
        Beat("bad_guys_close_in", "Bad Guys Close In", 0.60,
             "External pressure mounts while the internal team fractures."),
        Beat("all_is_lost", "All Is Lost", 0.68,
             "The opposite of the midpoint. Include a 'whiff of death' - "
             "something must actually end."),
        Beat("dark_night", "Dark Night of the Soul", 0.72,
             "The wallowing. Let them grieve before they solve it."),
        Beat("break_into_three", "Break Into Three", 0.77,
             "A and B story converge. The thematic truth becomes the solution."),
        Beat("finale", "Finale", 0.85,
             "They storm the castle, dismantle the old world and prove change."),
        Beat("final_image", "Final Image", 0.99,
             "The mirror of the opening image. Show how far they came."),
    ],
)

# --------------------------------------------------------------------------
# The Hero's Journey - Christopher Vogler's twelve stages
# --------------------------------------------------------------------------

HEROS_JOURNEY = Framework(
    key="heros_journey",
    name="The Hero's Journey",
    source="Christopher Vogler, The Writer's Journey (after Campbell)",
    note="The mythic spine. Best for quest, coming-of-age and epic fantasy.",
    beats=[
        Beat("ordinary_world", "Ordinary World", 0.02,
             "Establish the hero's flawed but familiar life."),
        Beat("call", "Call to Adventure", 0.10,
             "The problem or challenge arrives."),
        Beat("refusal", "Refusal of the Call", 0.15,
             "Fear speaks. What are they afraid to lose?"),
        Beat("mentor", "Meeting the Mentor", 0.20,
             "Guidance, training, or a gift that will matter later."),
        Beat("threshold", "Crossing the First Threshold", 0.25,
             "They commit and leave the known world behind."),
        Beat("tests", "Tests, Allies, Enemies", 0.35,
             "Learn the rules of the new world. Build the team."),
        Beat("approach", "Approach to the Inmost Cave", 0.45,
             "Preparation for the central ordeal. Dread builds."),
        Beat("ordeal", "The Ordeal", 0.50,
             "The hero faces death and their greatest fear."),
        Beat("reward", "Reward (Seizing the Sword)", 0.60,
             "They take the treasure - object, knowledge, or reconciliation."),
        Beat("road_back", "The Road Back", 0.72,
             "Consequences chase them. Recommit to finishing."),
        Beat("resurrection", "The Resurrection", 0.88,
             "The final, purest test. The old self dies for good."),
        Beat("elixir", "Return with the Elixir", 0.97,
             "They come home transformed, bearing something for others."),
    ],
)

# --------------------------------------------------------------------------
# Dan Harmon's Story Circle
# --------------------------------------------------------------------------

STORY_CIRCLE = Framework(
    key="story_circle",
    name="Dan Harmon's Story Circle",
    source="Dan Harmon",
    note=(
        "Eight steps, a compressed Hero's Journey. Superb for individual "
        "chapters and episodes, not just whole novels."
    ),
    beats=[
        Beat("you", "1. You", 0.05, "A character in a zone of comfort."),
        Beat("need", "2. Need", 0.15, "But they want something."),
        Beat("go", "3. Go", 0.25, "They enter an unfamiliar situation."),
        Beat("search", "4. Search", 0.40, "Adapt to it."),
        Beat("find", "5. Find", 0.50, "Get what they wanted."),
        Beat("take", "6. Take", 0.65, "Pay a heavy price for it."),
        Beat("return", "7. Return", 0.85, "Then return to their familiar situation."),
        Beat("change", "8. Change", 0.97, "Having changed."),
    ],
)

# --------------------------------------------------------------------------
# Dan Wells' Seven-Point Structure - built backward from the resolution
# --------------------------------------------------------------------------

SEVEN_POINT = Framework(
    key="seven_point",
    name="Seven-Point Structure",
    source="Dan Wells",
    note=(
        "Fill this in BACKWARD. Write the Resolution first, then the Hook as "
        "its mirror image, then the middle. That is the whole trick."
    ),
    beats=[
        Beat("hook", "Hook", 0.01,
             "The opposite of your resolution. Start where the character is "
             "not yet who they will become. (Write this SECOND.)"),
        Beat("plot_turn_1", "Plot Turn 1", 0.25,
             "The call to adventure. The world changes and the conflict begins."),
        Beat("pinch_1", "Pinch Point 1", 0.37,
             "Apply pressure. Introduce the antagonist's force. Something fails."),
        Beat("midpoint", "Midpoint", 0.50,
             "The shift from reaction to action. They stop reacting and decide."),
        Beat("pinch_2", "Pinch Point 2", 0.62,
             "Crush them. The lowest pressure point - the mentor dies, the "
             "team fails, the plan collapses."),
        Beat("plot_turn_2", "Plot Turn 2", 0.75,
             "They get the final piece - the knowledge or resolve needed to "
             "win. Everything needed for victory is now in hand."),
        Beat("resolution", "Resolution", 0.97,
             "The end state. The character's arc completes. "
             "(Write this FIRST.)"),
    ],
)

# --------------------------------------------------------------------------
# Freytag's Pyramid
# --------------------------------------------------------------------------

FREYTAG = Framework(
    key="freytag",
    name="Freytag's Pyramid",
    source="Gustav Freytag, Die Technik des Dramas",
    note="The classical five-part dramatic arc. Useful for tragedy.",
    beats=[
        Beat("exposition", "Exposition", 0.05, "Establish world, character, status quo."),
        Beat("inciting", "Inciting Incident", 0.12, "The disturbance."),
        Beat("rising", "Rising Action", 0.35, "Complications accumulate."),
        Beat("climax", "Climax", 0.50, "The turning point of fortune."),
        Beat("falling", "Falling Action", 0.70, "Consequences unspool."),
        Beat("denouement", "Resolution / Denouement", 0.90, "Tension releases."),
        Beat("catastrophe", "Catastrophe or Restoration", 0.98,
             "Tragedy ends in ruin; comedy ends in restored order."),
    ],
)

# --------------------------------------------------------------------------
# Romancing the Beat - Gwen Hayes' romance structure
# --------------------------------------------------------------------------

ROMANCE_BEAT = Framework(
    key="romance_beat",
    name="Romancing the Beat",
    source="Gwen Hayes, Romancing the Beat",
    note=(
        "The romance arc runs in parallel with the plot arc. Both leads need "
        "a want, a need and a wound."
    ),
    beats=[
        Beat("no_mate", "No Mate in Sight", 0.02,
             "Each lead's ordinary world and the emotional wound that makes "
             "love feel impossible."),
        Beat("meet", "Meet Cute / Inciting Incident", 0.10,
             "First contact. Sparks, friction, or both."),
        Beat("adhesion", "No Way / Adhesion", 0.18,
             "Why they cannot walk away from each other - the plot forces "
             "proximity."),
        Beat("inkling_desire", "Inkling of Desire", 0.25,
             "First crack in the armour. Attraction registers."),
        Beat("deepening_desire", "Deepening Desire", 0.35,
             "Shared vulnerability. They see each other truly."),
        Beat("maybe_works", "Maybe This Could Work", 0.45,
             "Hope. They imagine a future."),
        Beat("midpoint_love", "Midpoint of Love", 0.50,
             "The high point - a kiss, a confession, a night together. "
             "Emotional commitment outruns readiness."),
        Beat("inkling_doubt", "Inkling of Doubt", 0.58,
             "The wound stirs. Old fear resurfaces."),
        Beat("deepening_doubt", "Deepening Doubt", 0.66,
             "Self-protection kicks in. They start pulling away."),
        Beat("retreat", "Retreat", 0.72,
             "Withdrawal. Each retreats into the lie they believe."),
        Beat("breakup", "Break Up / Black Moment", 0.78,
             "The relationship ends. It must feel genuinely final."),
        Beat("dark_night", "Dark Night of the Soul", 0.84,
             "Each lead alone, confronting what they actually need."),
        Beat("grand_gesture", "Grand Gesture", 0.92,
             "Proof of change - a risk taken, a pride swallowed, a truth told."),
        Beat("hea", "Happily Ever After", 0.98,
             "The earned union. Deliver the genre promise."),
    ],
)

# --------------------------------------------------------------------------
# Mystery / crime / thriller
# --------------------------------------------------------------------------

MYSTERY = Framework(
    key="mystery",
    name="Mystery / Crime Structure",
    source="Composite of standard detective-fiction practice",
    note=(
        "Play fair: every clue the detective sees, the reader sees. Track "
        "clues and red herrings in the Clue Tracker."
    ),
    beats=[
        Beat("hook_crime", "The Crime / Hook", 0.02,
             "The body, the theft, the disappearance. Establish stakes."),
        Beat("sleuth_intro", "Sleuth Introduced", 0.06,
             "Show competence and the personal flaw the case will exploit."),
        Beat("investigation", "Investigation Begins", 0.15,
             "The sleuth commits. Establish method and the rules of the world."),
        Beat("suspects", "Suspects Assembled", 0.25,
             "Everyone has motive, means and opportunity. Everyone lies "
             "about something."),
        Beat("first_clue", "First Real Clue", 0.32,
             "A genuine piece of the truth, buried in noise."),
        Beat("red_herring", "Red Herring", 0.40,
             "A plausible wrong path. It must be honestly misleading, not "
             "a cheat."),
        Beat("complication", "Second Crime / Complication", 0.48,
             "The stakes escalate. The sleuth's presence made things worse."),
        Beat("midpoint_reveal", "Midpoint Revelation", 0.50,
             "The case is not what it appeared. Reframe the question."),
        Beat("dead_end", "Dead End", 0.62,
             "The leading theory collapses. Personal cost lands."),
        Beat("darkest", "Darkest Moment", 0.72,
             "The sleuth is discredited, endangered, or off the case."),
        Beat("breakthrough", "Breakthrough", 0.80,
             "The overlooked detail from earlier snaps into place."),
        Beat("confrontation", "Confrontation", 0.90,
             "Sleuth versus culprit. Physical or intellectual jeopardy."),
        Beat("reveal", "The Reveal", 0.95,
             "Lay out the chain of reasoning. Reward the attentive reader."),
        Beat("denouement", "Denouement", 0.99,
             "Consequences, cost, and what the case did to the sleuth."),
    ],
)

# --------------------------------------------------------------------------
# The Snowflake Method - a process, not a beat sheet
# --------------------------------------------------------------------------

SNOWFLAKE = Framework(
    key="snowflake",
    name="The Snowflake Method",
    source="Randy Ingermanson",
    note=(
        "A ten-step design PROCESS, not positions in the manuscript. Each "
        "step expands the previous one. Expect to revise earlier steps as "
        "later ones teach you things."
    ),
    beats=[
        Beat("step1", "Step 1 - One Sentence", None,
             "Summarise the novel in fifteen words or fewer. No character "
             "names - use roles. This becomes your pitch."),
        Beat("step2", "Step 2 - One Paragraph", None,
             "Expand to five sentences: setup, disaster one, disaster two, "
             "disaster three, ending. Three disasters, one resolution."),
        Beat("step3", "Step 3 - Character Summaries", None,
             "One page per major character: name, one-sentence storyline, "
             "motivation (abstract), goal (concrete), conflict, epiphany."),
        Beat("step4", "Step 4 - One-Page Synopsis", None,
             "Expand each sentence of Step 2 into a full paragraph. All but "
             "the last should end in disaster."),
        Beat("step5", "Step 5 - Character Charters", None,
             "A page per major character in their own voice; half a page for "
             "minor ones. What does the story look like from inside them?"),
        Beat("step6", "Step 6 - Four-Page Synopsis", None,
             "Expand each synopsis paragraph to a full page."),
        Beat("step7", "Step 7 - Character Bibles", None,
             "Full detail: physical, background, psychology, voice. Go deep "
             "enough that dialogue starts writing itself."),
        Beat("step8", "Step 8 - Scene List", None,
             "One line per scene: POV, what happens. This is your build order."),
        Beat("step9", "Step 9 - Scene Narration", None,
             "A paragraph or page per scene - the multi-paragraph plan. "
             "Optional; skip if it kills your momentum."),
        Beat("step10", "Step 10 - Write the First Draft", None,
             "You now know the story. Go fast and do not look back."),
    ],
)

# --------------------------------------------------------------------------
# Scene & Sequel - Dwight Swain / Jack Bickham, applied per scene
# --------------------------------------------------------------------------

SCENE_UNIT = [
    ("goal", "Goal",
     "What does the POV character want in THIS scene? Concrete and stateable."),
    ("conflict", "Conflict",
     "What or who stands in the way? Escalate the opposition."),
    ("disaster", "Disaster",
     "How does it go wrong? Yes-but, or No-and-furthermore. Never a clean win."),
]

SEQUEL_UNIT = [
    ("reaction", "Reaction",
     "The emotional aftermath. Let them feel it before they think."),
    ("dilemma", "Dilemma",
     "All available options are bad. Show the reasoning."),
    ("decision", "Decision",
     "They choose, which becomes the goal of the next scene."),
]

# --------------------------------------------------------------------------
# Character arc - K.M. Weiland's Lie/Truth framework
# --------------------------------------------------------------------------

ARC_TYPES = [
    ("positive_change", "Positive Change Arc",
     "Believes a Lie, is forced to confront it, and embraces the Truth."),
    ("flat", "Flat Arc",
     "Already holds the Truth. The world resists; they change the world."),
    ("negative_disillusionment", "Negative Arc - Disillusionment",
     "Believes a Lie, learns the Truth, and the Truth is devastating."),
    ("negative_fall", "Negative Arc - Fall",
     "Believes a Lie, is offered the Truth, and chooses a deeper Lie."),
    ("negative_corruption", "Negative Arc - Corruption",
     "Sees the Truth, is surrounded by it, and rejects it for the Lie."),
]

# --------------------------------------------------------------------------
# The four tiers of revision
# --------------------------------------------------------------------------

REVISION_TIERS = [
    ("developmental", "1. Developmental Edit (Structure)",
     [
         "Does the premise deliver on its promise?",
         "Is there a clear protagonist with a want, a need, and a flaw?",
         "Does every act break land in roughly the right place?",
         "Does each scene change the situation? Cut any that do not.",
         "Is the midpoint a genuine pivot from reaction to action?",
         "Is the climax the answer to the question page one asked?",
         "Are subplots resolved or deliberately left open?",
         "Does the theme emerge from events rather than being announced?",
     ]),
    ("line", "2. Line Edit (Flow & Clarity)",
     [
         "Read aloud. Mark every place you stumble.",
         "Vary sentence length - check the rhythm map.",
         "Replace weak verb + adverb with one strong verb.",
         "Cut filter words: felt, saw, heard, noticed, realised, watched.",
         "Cut throat-clearing at the start of scenes and chapters.",
         "Make every character's dialogue sound like only them.",
         "Ground each scene in at least three senses beyond sight.",
         "Check paragraph openings - avoid starting many with the same word.",
     ]),
    ("copy", "3. Copy Edit (Consistency)",
     [
         "Names, ages, eye colours, and place names consistent throughout.",
         "Timeline holds - days of the week, seasons, travel times.",
         "Dialogue punctuation: commas and periods INSIDE the quotes (US).",
         "Dialogue tags lowercase after a comma: \"...,\" he said.",
         "Em dash for interruption; ellipsis for a trailing-off.",
         "One style for numbers, capitalisation and invented terms.",
         "Chicago Manual of Style for anything ambiguous.",
         "Check the invented-terms glossary against the manuscript.",
     ]),
    ("proof", "4. Proofread (Typos)",
     [
         "Spellcheck, then read backward by paragraph to defeat familiarity.",
         "Homophones: their/there, its/it's, lead/led, discreet/discrete.",
         "Double spaces, double words, missing quotation marks.",
         "Chapter numbering and headers correct and sequential.",
         "Scene breaks present and consistently marked.",
         "No leftover [bracket tags] or placeholder text.",
         "Front matter and back matter complete.",
     ]),
]

# --------------------------------------------------------------------------
# Writer's block diagnostic
# The percentages and interventions come from the productivity blueprint.
# --------------------------------------------------------------------------


class BlockType(NamedTuple):
    key: str
    name: str
    share: str
    root_cause: str
    symptom: str
    question: str
    fix: str
    timeline: str
    interventions: List[str]


BLOCK_TYPES: List[BlockType] = [
    BlockType(
        "physiological", "Physiological", "42%",
        "Stress, exhaustion or illness",
        "Everything feels hard; physical tension; mental fog",
        "Is everything feeling hard right now - not just the writing?",
        "Rest, not discipline. Real breaks and short forced sessions.",
        "Days to weeks",
        [
            "Stop. This is not a willpower problem and pushing will deepen it.",
            "Sleep, food, water, daylight, movement - in that order.",
            "If you must write, cap it at 15-20 minutes and then genuinely stop.",
            "Lower the daily target for this week. Protect the streak, not the volume.",
        ],
    ),
    BlockType(
        "motivational", "Motivational", "29%",
        "Fear of judgement; avoidance",
        "Can write if forced, but resists sitting down",
        "Could we write if someone made us?",
        "Low-stakes drafting nobody will ever read; talk it out loud first.",
        "1-2 weeks",
        [
            "Open the Scratchpad, not the manuscript. Nothing there counts.",
            "Write the scene as a letter to a friend explaining what happens.",
            "Set a 10-minute sprint. The goal is starting, not quality.",
            "Name the reader you are afraid of, then write for someone else.",
        ],
    ),
    BlockType(
        "cognitive", "Cognitive", "13%",
        "Perfectionism; premature editing",
        "Deleting sentences immediately after writing them",
        "Do we delete sentences immediately after writing them?",
        "Separate drafting from editing. Timed blocks. Hide the text.",
        "4-6 sessions",
        [
            "Turn on Ghost Mode - typed text fades so you cannot reread it.",
            "Drafting days and editing days are different days. Never both.",
            "Drop a [fix later] tag instead of solving the problem now.",
            "Bad prose is fixable. A blank page is not.",
        ],
    ),
    BlockType(
        "behavioural", "Behavioural", "11%",
        "Poor habits; lack of routine",
        "No consistent schedule or dedicated space",
        "Do we lack a regular writing time?",
        "Habit tracking and a distraction lockdown.",
        "2-4 weeks",
        [
            "Pick one fixed time tomorrow and defend it. Same time daily.",
            "One place, one ritual - the cue matters more than the duration.",
            "Watch the streak on the dashboard. Do not break the chain.",
            "Close the browser before you open the manuscript.",
        ],
    ),
    BlockType(
        "composition", "Composition", "5%",
        "Translation difficulty",
        "Ideas exist, but sentences will not form",
        "Can we explain it aloud but not write it?",
        "Dictate it. Rehearse the scene out loud, then transcribe.",
        "2-4 weeks",
        [
            "Say the scene out loud as if telling someone what happens.",
            "Use Windows dictation (Win+H) straight into the editor.",
            "Write the ugliest possible version in short simple sentences.",
            "One clause per line. Join them into prose afterwards.",
        ],
    ),
]

# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------

FRAMEWORKS: Dict[str, Framework] = {
    f.key: f
    for f in (
        THREE_ACT,
        SAVE_THE_CAT,
        HEROS_JOURNEY,
        STORY_CIRCLE,
        SEVEN_POINT,
        FREYTAG,
        ROMANCE_BEAT,
        MYSTERY,
        SNOWFLAKE,
    )
}

FRAMEWORK_ORDER = [
    "three_act",
    "save_the_cat",
    "seven_point",
    "story_circle",
    "heros_journey",
    "romance_beat",
    "mystery",
    "freytag",
    "snowflake",
]


def framework(key: str) -> Framework:
    return FRAMEWORKS.get(key, THREE_ACT)


def framework_names() -> List[str]:
    return [FRAMEWORKS[k].name for k in FRAMEWORK_ORDER]


def key_for_name(name: str) -> str:
    for key in FRAMEWORK_ORDER:
        if FRAMEWORKS[key].name == name:
            return key
    return "three_act"


def target_word_for_beat(beat: Beat, total_words: int) -> Optional[int]:
    """Where in the manuscript this beat should land, in words."""
    if beat.pct is None or not total_words:
        return None
    return int(round(beat.pct * total_words))
