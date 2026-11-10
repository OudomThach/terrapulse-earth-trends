"""Stage 3 · Around the world: the same variable at every place, so opposite trends show up side by side."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from terrapulse import charts, narrative as N, ui
from terrapulse.case import CaseContext
from terrapulse.climate import PLACES
from terrapulse.variables import CODES, VARIABLES, Variable

from . import common as C


def _finding(reg: pd.DataFrame, v: Variable) -> None:
    """Headline about the signs of the significant places (opposite stories, or all one way)."""
    rising = reg[reg["significant"] & (reg["per_decade"] > 0)]
    falling = reg[reg["significant"] & (reg["per_decade"] < 0)]
    st.markdown(ui.kpi_row([
        ui.kpi("Significantly rising", str(len(rising)), f"of {len(reg)} places", "rise"),
        ui.kpi("Significantly falling", str(len(falling)), f"of {len(reg)} places", "fall"),
        ui.kpi("No clear trend", str(len(reg) - len(rising) - len(falling)), "natural variation can't be ruled out")]),
        unsafe_allow_html=True)
    if len(rising) and len(falling):
        hi, lo = rising.sort_values("per_decade").iloc[-1], falling.sort_values("per_decade").iloc[0]
        text = (f"**{v.name}** is rising in **{hi['name']}** ({N.signed(hi['per_decade'], v.decimals)} {v.unit}/decade) "
                f"but falling in **{lo['name']}** ({N.signed(lo['per_decade'], v.decimals)}). "
                "A single global average would hide both.")
        st.markdown(ui.banner("Same variable, opposite stories", ui.md_bold_to_html(text), "sig",
                              eyebrow="Detective's finding"), unsafe_allow_html=True)
    elif len(rising) or len(falling):
        way = "rising" if len(rising) else "falling"
        st.markdown(ui.banner(f"Every significant place is {way}", ui.md_bold_to_html(
            f"No place shows a significant move in the opposite direction for **{v.name.lower()}** in this window."),
            "sig", eyebrow="Detective's finding"), unsafe_allow_html=True)


def render(ctx: CaseContext) -> None:
    """Draw the map, the ranking and the opposite-stories finding for one variable."""
    st.markdown(ui.section("Same question, everywhere",
                           "The same variable can rise in one place and fall in another, even when one process drives "
                           "both. Pick a variable and compare all places."), unsafe_allow_html=True)
    st.session_state.setdefault("map_var", st.session_state["var"])
    c1, c2, c3 = st.columns([4, 2, 2])
    with c1:
        code = st.selectbox("Variable", CODES, key="map_var",
                            format_func=lambda c: f"{VARIABLES[c].name}  ·  {VARIABLES[c].group}")
    with c2:
        satellite = st.toggle("Satellite imagery", value=True, key="sat")
    with c3:
        live = st.toggle("Live natural events", value=False, key="live",
                         help="Currently active wildfires, storms and sea-ice events from an open event feed.")
    v = VARIABLES[code]
    place = ctx.place
    extra = None if place.name in PLACES else (place.name, place.lat, place.lon, place.biome, place.blurb)
    reg = C.get_regional(code, ctx.start, ctx.end, extra)
    if reg.empty:
        st.info("This variable has no testable record in the chosen window.")
        return
    _finding(reg, v)

    events = C.get_events() if live else None
    if live and events is None:
        st.warning("The live event feed is not reachable right now. The trend map is unaffected.")
    st.markdown(ui.direction_legend(), unsafe_allow_html=True)
    C.show(charts.map_figure(reg, v, satellite=satellite, selected=place.name, events=events), key="map")
    st.caption("Large ringed dots are statistically significant after correcting for comparing many places; small "
               "faded dots are not. Colour shows the direction and size of change per decade.")

    st.markdown(ui.section("Ranked", "Same data as the map, sorted from most-falling to most-rising."),
                unsafe_allow_html=True)
    C.show(charts.trend_bars_figure(reg, v), key="bars")
    o1, o2 = st.columns([3, 2], gap="large")
    with o1:
        pick = st.selectbox("Open a place from this list", list(reg["name"]), index=None,
                            placeholder="Choose a place to investigate", key="open_pick")
    with o2:
        st.write("")
        st.write("")
        if pick and pick in PLACES:
            st.button(f"Investigate {pick} →", on_click=C.open_place, args=(pick,), type="primary")
    with st.expander("View the data table"):
        table = reg.assign(per_decade=reg["per_decade"].round(4), p=reg["p"].round(4), q=reg["q"].round(4))
        st.dataframe(table[["name", "biome", "per_decade", "p", "q", "significant", "jump"]],
                     hide_index=True, width="stretch")
