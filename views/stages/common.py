"""Shared plumbing for the Trend Detective page: stage names, demo cases, session state, button
callbacks, cached data loaders and a chart helper. Nothing here draws a stage."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from terrapulse import trends as T
from terrapulse.climate import FIRST_YEAR, LAST_YEAR, PLACES, Place, fetch_events, load_monthly
from terrapulse.questions import QUESTIONS_BY_ID
from terrapulse.variables import CODES, VARIABLES

# ----------------------------------------------------------------------------- stages
S_SUSPECTS, S_EVIDENCE, S_WHERE, S_LINKS, S_HOW = (
    "1 · Suspects", "2 · Evidence", "3 · Around the world", "4 · Connections", "5 · How it works")
STAGES = [S_SUSPECTS, S_EVIDENCE, S_WHERE, S_LINKS, S_HOW]

ALL_CLUES = "All 20 clues"
SURPRISE = "Surprise me"

# ----------------------------------------------------------------------------- demo investigations
CASES = [
    dict(title="The Arctic fast lane", place="Svalbard, Arctic", var="T2M_MIN", stage=S_EVIDENCE,
         text="Does the far north warm faster than the rest of the planet? Look at the nights."),
    dict(title="Cooling in a warming world", place="Delhi & Gangetic plain", var="ALLSKY_SFC_SW_DWN", stage=S_EVIDENCE,
         text="One of few places where the air is not warming. Follow the sunlight and the haze."),
    dict(title="The roof of the world turns wetter", place="Tibetan Plateau", var="PRECTOTCORR", stage=S_EVIDENCE,
         text="Warmer and wetter at once. How many vital signs shift together?"),
    dict(title="Trend or data glitch?", place="Greenland ice sheet", var="CLOUD_AMT", stage=S_EVIDENCE,
         text="A 'significant' trend that hides a sudden jump. Can the detective catch it?"),
    dict(title="Heat on the Mediterranean", place="Mediterranean Spain", var="T2M", stage=S_SUSPECTS,
         text="A climate-change hotspot: scan everything and see what stands out."),
]


# ----------------------------------------------------------------------------- session state
def init_state() -> None:
    """Create every session-state key once and read a shared link (?place=&stage=&var=&q=&from=&to=)."""
    defaults = {"place": "Svalbard, Arctic", "win": (FIRST_YEAR, LAST_YEAR), "stage": S_SUSPECTS, "var": "T2M",
                "question": ALL_CLUES, "clat": 13.1, "clon": 103.2}
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    if "_init" in st.session_state:
        return
    qp = st.query_params
    if qp.get("place") in PLACES:
        st.session_state["place"] = qp["place"]
    if qp.get("stage", "").isdigit() and 1 <= int(qp["stage"]) <= len(STAGES):
        st.session_state["stage"] = STAGES[int(qp["stage"]) - 1]
    if qp.get("var") in VARIABLES:
        st.session_state["var"] = qp["var"]
    if qp.get("q") in QUESTIONS_BY_ID:
        st.session_state["question"] = QUESTIONS_BY_ID[qp["q"]].text
    elif qp.get("q") == "surprise":
        st.session_state["question"] = SURPRISE
    if qp.get("from", "").isdigit() and qp.get("to", "").isdigit():
        a, b = int(qp["from"]), int(qp["to"])
        if FIRST_YEAR <= a < b <= LAST_YEAR:
            st.session_state["win"] = (a, b)
    st.session_state["_init"] = True


def question_param(choice: str | None) -> str | None:
    """The ?q= value for the current question choice (None for 'all clues')."""
    from terrapulse.questions import QUESTIONS_BY_TEXT
    if choice == SURPRISE:
        return "surprise"
    return QUESTIONS_BY_TEXT[choice].id if choice in QUESTIONS_BY_TEXT else None


# ----------------------------------------------------------------------------- button callbacks
def start_case(case: dict) -> None:
    """Load a demo investigation: place, clue and stage."""
    st.session_state.update(place=case["place"], win=(FIRST_YEAR, LAST_YEAR), var=case["var"], stage=case["stage"],
                            question=ALL_CLUES)


def investigate(code: str) -> None:
    """Jump from a suspect card to its full evidence."""
    st.session_state.update(var=code, stage=S_EVIDENCE)


def retest_from(year: int, end: int) -> None:
    """Re-run the analysis from the year after a suspected data jump."""
    st.session_state.update(win=(year, end))


def open_place(name: str) -> None:
    """Open a place picked from the world map."""
    st.session_state.update(place=name, stage=S_SUSPECTS, question=ALL_CLUES)


def reset_window() -> None:
    """Restore the full 1990 to 2025 window."""
    st.session_state.update(win=(FIRST_YEAR, LAST_YEAR))


# ----------------------------------------------------------------------------- cached data
@st.cache_data(show_spinner="Reading 36 years of satellite records...")
def get_record(lat: float, lon: float) -> pd.DataFrame:
    """Monthly record for a place (disk-cached by the data layer)."""
    return load_monthly(lat, lon)


@st.cache_data(show_spinner="Testing every variable for trends...")
def get_scan(lat: float, lon: float, start: int, end: int) -> dict:
    """Trend test of every variable, with false-discovery-corrected q-values."""
    return T.scan(get_record(lat, lon), CODES, start, end)


@st.cache_data(show_spinner="Comparing places...")
def get_regional(code: str, start: int, end: int, extra: tuple | None = None) -> pd.DataFrame:
    """One variable's trend at every built-in place (plus the user's custom spot)."""
    rows = []
    places = list(PLACES.values()) + ([Place(*extra)] if extra else [])
    for p in places:
        r = T.analyze(get_record(p.lat, p.lon)[code], code, start, end)
        if r.usable:
            rows.append(dict(name=p.name, lat=p.lat, lon=p.lon, biome=p.biome, per_decade=r.per_decade, p=r.p,
                             jump=r.suspicious_jump))
    df = pd.DataFrame(rows)
    if len(df):
        df["q"] = T.benjamini_hochberg(df["p"].to_numpy())     # correct for comparing many places
        df["significant"] = df["q"] < 0.05
    return df


@st.cache_data(show_spinner="Reading how the variables move together...")
def get_corr(lat: float, lon: float, start: int, end: int) -> pd.DataFrame:
    """Link strengths between all variables at a place (cached)."""
    return T.detrended_anomaly_correlations(get_record(lat, lon), CODES, start, end)


@st.cache_data(ttl=3600, show_spinner="Checking live natural events...")
def get_events() -> pd.DataFrame | None:
    """Currently active natural events, or None if the open feed cannot be reached."""
    try:
        return fetch_events()
    except Exception:
        return None


def show(fig, key: str | None = None) -> None:
    """Render a Plotly figure with our own theme and no toolbar."""
    st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False}, key=key)
