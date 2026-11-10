"""Guided questions: turn a plain-English curiosity into a verdict backed by the trend tests.

A ``Question`` lists the *clues* (variables) that bear on it and which direction of change counts as "yes".
``answer`` reads the scan results and reports whether the clues agree. Pure functions, no UI, so the logic
can be tested and reused by any front end.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .narrative import rate_text
from .trends import TrendResult
from .variables import VARIABLES

SIGNIFICANT_Q = 0.05


@dataclass(frozen=True)
class Question:
    """One guided question.

    ``clues`` maps a variable code to a polarity: +1 if a RISE in that variable answers "up",
    -1 if a FALL does (for example, fewer frost days means the cold season is shrinking).
    """

    id: str
    text: str
    why: str
    clues: dict[str, int]
    up: str       # headline when the clues agree on the "up" direction
    down: str     # headline when they agree on the opposite direction
    none: str     # headline when no clue shows a significant change


QUESTIONS: list[Question] = [
    Question("hotter", "Is it getting hotter?",
             "Compares four temperature records: daily average, daytime high, night-time low and surface skin.",
             {"T2M": 1, "T2M_MAX": 1, "T2M_MIN": 1, "TS": 1},
             "Yes, it is warming", "No, it is cooling", "No clear change in temperature"),
    Question("land", "Is the land getting wetter or drier?",
             "Looks at rainfall and at soil moisture near the surface and down at the roots.",
             {"PRECTOTCORR": 1, "GWETROOT": 1, "GWETTOP": 1},
             "The land is getting wetter", "The land is getting drier", "No clear change in rain or soil moisture"),
    Question("airwater", "Is the air holding more moisture?",
             "Checks water vapour in the air as a share of capacity (humidity) and in absolute terms.",
             {"QV2M": 1, "TQV": 1, "RH2M": 1},
             "Yes, there is more moisture in the air", "The air is getting drier", "No clear change in air moisture"),
    Question("sun", "Is the sunlight changing?",
             "Combines sunshine reaching the ground, cloud cover and haze: less cloud and haze means brighter.",
             {"ALLSKY_SFC_SW_DWN": 1, "CLOUD_AMT": -1, "AOD_55": -1},
             "It is getting brighter", "It is getting dimmer", "No clear change in sunlight"),
    Question("trap", "Is the sky trapping more heat?",
             "Looks at the infrared heat sent back down, plus water vapour and cloud, which both hold heat in.",
             {"ALLSKY_SFC_LW_DWN": 1, "QV2M": 1, "TQV": 1, "CLOUD_AMT": 1},
             "Yes, the atmosphere is holding in more heat", "It is trapping less heat",
             "No clear change in heat trapping"),
    Question("cold", "Is the cold season shrinking?",
             "Counts freezing days and snow depth: fewer of both means a shrinking cold season.",
             {"FROST_DAYS": -1, "SNODP": -1},
             "Yes, there is less frost and snow", "No, there is more frost and snow",
             "No clear change in frost or snow (or none to measure here)"),
    Question("wind", "Is it getting windier?",
             "Follows average wind speed 10 metres above the ground.",
             {"WS10M": 1}, "Yes, it is windier", "It is calmer", "No clear change in wind"),
    Question("ozone", "Is the ozone shield changing?",
             "Follows the total ozone in the air above the place, which screens ultraviolet light.",
             {"TO3": 1}, "The ozone layer is getting thicker", "The ozone layer is getting thinner",
             "No clear change in ozone"),
]

QUESTIONS_BY_ID = {q.id: q for q in QUESTIONS}
QUESTIONS_BY_TEXT = {q.text: q for q in QUESTIONS}


@dataclass
class Answer:
    """The detective's reading of one question."""

    outcome: str                      # up | down | mixed | none | unknown
    headline: str
    body: str
    codes: list[str] = field(default_factory=list)   # clues examined, strongest evidence first

    @property
    def tone(self) -> str:
        """Banner tone for the UI: a clear answer reads as 'sig', a muddled one as 'weak'."""
        return {"up": "sig", "down": "sig", "mixed": "weak"}.get(self.outcome, "none")


def _is_clear(res: TrendResult | None) -> bool:
    """A clue counts only if it is testable, significant after correction, and not a suspected data jump."""
    return bool(res and res.usable and res.q < SIGNIFICANT_Q and not res.suspicious_jump)


def answer(question: Question, results: dict[str, TrendResult]) -> Answer:
    """Decide whether the clues agree on an answer."""
    tested = [c for c in question.clues if results.get(c) is not None and results[c].usable]
    if not tested:
        return Answer("unknown", "We cannot answer this here",
                      "None of the clues for this question has a usable record at this place.")
    ranked = sorted(tested, key=lambda c: (results[c].q, -abs(results[c].z)))
    up = [c for c in ranked if _is_clear(results[c]) and results[c].slope * question.clues[c] > 0]
    down = [c for c in ranked if _is_clear(results[c]) and results[c].slope * question.clues[c] < 0]
    flagged = [c for c in tested if results[c].usable and results[c].q < SIGNIFICANT_Q and results[c].suspicious_jump]

    def strongest(codes: list[str]) -> str:
        """Sentence naming the clue with the strongest evidence in ``codes``."""
        v = VARIABLES[codes[0]]
        return f"Strongest clue: {v.name.lower()}, {rate_text(v, results[codes[0]])}."

    if up and not down:
        outcome, headline = "up", question.up
        body = f"{len(up)} of {len(tested)} clues moved this way significantly. {strongest(up)}"
    elif down and not up:
        outcome, headline = "down", question.down
        body = f"{len(down)} of {len(tested)} clues moved this way significantly. {strongest(down)}"
    elif up and down:
        outcome, headline = "mixed", "A mixed picture"
        body = (f"{len(up)} clue(s) point one way and {len(down)} the other, which usually means more than one process "
                f"is at work. Open each clue to see which. {strongest(up)}")
    else:
        outcome, headline = "none", question.none
        best = results[ranked[0]]
        body = (f"None of the {len(tested)} clues passed the significance test. "
                f"Closest: {VARIABLES[ranked[0]].name.lower()}, {rate_text(VARIABLES[ranked[0]], best)}, "
                f"adjusted p = {best.q:.2f}. A longer record can still reveal a slow trend.")
    if flagged:
        names = ", ".join(VARIABLES[c].name.lower() for c in flagged)
        body += f" (Left out because of a possible data jump: {names}.)"
    return Answer(outcome, headline, body, ranked)


def surprise_me(results: dict[str, TrendResult], k: int = 3) -> list[str]:
    """The ``k`` clearest signals at this place, ignoring suspected data jumps."""
    clean = [r for r in results.values() if r.usable and not r.suspicious_jump]
    clean.sort(key=lambda r: (r.q, -abs(r.z)))
    return [r.code for r in clean[:k]]
