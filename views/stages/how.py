"""Stage 5 · How it works: method in five steps, glossary, variable dictionary and honest limits."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from terrapulse import ui
from terrapulse.case import CaseContext
from terrapulse.climate import FIRST_YEAR
from terrapulse.variables import VARIABLES

STEPS = [
    ("STEP 1", "Pick the clues", "20 vital signs of the Earth system: temperature, water, land, sunlight and air."),
    ("STEP 2", "Get the record", "Monthly values from 1990 to 2025 at your chosen spot, from satellite-driven reanalysis."),
    ("STEP 3", "Average whole years", "Yearly averages cancel the seasons, so winter and summer cannot fake a trend."),
    ("STEP 4", "Test the trend", "Mann-Kendall test for a rise or fall, Sen's slope for the rate, and a 95% confidence range."),
    ("STEP 5", "Be sceptical", "Corrections for testing many variables, for year-to-year memory, and a check for sudden jumps."),
]

GLOSSARY = {
    "Trend": "A steady tendency to rise or fall over many years, as opposed to ordinary ups and downs.",
    "Significant": "Unlikely to be luck. We use p < 0.05: if nothing were changing, a pattern this strong would appear less than 5 times in 100.",
    "p-value": "The chance of seeing a pattern at least this strong if there were no real trend. Small means convincing.",
    "Mann-Kendall test": "Compares every pair of years and counts how often the later one is higher. Works without assuming a bell-shaped spread and is not thrown off by outliers.",
    "Sen's slope": "The median of the slopes between every pair of years: the rate of change, resistant to outliers.",
    "Confidence range (95%)": "The span of rates that fit the data. If it includes zero, 'no change' remains plausible.",
    "Anomaly": "A value minus the long-term average for that calendar month: how unusual it is for the season.",
    "False-discovery correction": "Test 20 things and one will look significant by chance. Benjamini-Hochberg adjusts the p-values to account for that.",
    "Autocorrelation": "A wet year tends to be followed by another wet year. Strong 'memory' makes trends look more convincing than they are, so we adjust.",
    "Step change": "A sudden jump instead of a steady slope, often caused by a change in instruments or data processing rather than climate.",
    "Reanalysis": "A weather model constantly corrected with satellite and ground observations to give a complete, consistent record.",
}

LIMITS = (
    "- **A trend says what, not why.** Linking a trend to a cause takes more evidence than one statistic.\n"
    "- **Each data cell is roughly 50 km wide.** Results describe a region, not one street or city.\n"
    "- **Reanalysis blends model and observations.** Changes in the observing system can create artificial "
    "jumps, which is why the detective flags abrupt steps (the Greenland cloud case is a real example).\n"
    "- **36 years is short for slow climate signals.** Natural cycles such as El Niño can masquerade as trends "
    "over a few decades.\n- **Linear trends only.** A curved or reversing change is summarised by one straight line.")


def render(ctx: CaseContext) -> None:
    """Draw the method, glossary, variable dictionary and limits."""
    st.markdown(ui.section("How the detective works", "Five steps, all classic statistics you can check yourself."),
                unsafe_allow_html=True)
    st.markdown('<div class="tp-how">' + "".join(
        f'<div class="card"><div class="n">{a}</div><h4>{b}</h4><p>{c}</p></div>' for a, b, c in STEPS) + "</div>",
        unsafe_allow_html=True)

    st.markdown(ui.section("Glossary"), unsafe_allow_html=True)
    for term, text in GLOSSARY.items():
        with st.expander(term):
            st.markdown(text)

    st.markdown(ui.section("The variables"), unsafe_allow_html=True)
    catalog = pd.DataFrame([{"Variable": v.name, "Type": v.group, "Unit": v.unit, "What it is": v.definition,
                             "Record starts": v.since or FIRST_YEAR} for v in VARIABLES.values()])
    st.dataframe(catalog, hide_index=True, width="stretch")

    st.markdown(ui.section("Honest limits"), unsafe_allow_html=True)
    st.markdown(LIMITS)
