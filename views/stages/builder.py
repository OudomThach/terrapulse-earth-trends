"""The sidebar (demo cases) and the case builder (place + years) that sit above every stage."""

from __future__ import annotations

import streamlit as st

from terrapulse import ui
from terrapulse.case import CaseContext
from terrapulse.climate import CUSTOM, FIRST_YEAR, LAST_YEAR, PLACES, ClimateDataError, Place

from . import common as C


def render_sidebar() -> None:
    """Five one-click demo investigations."""
    with st.sidebar:
        st.markdown('<div class="tp-eyebrow">Watch a demo</div>', unsafe_allow_html=True)
        st.caption("Five ready-made investigations. Each one loads a place and a clue for you.")
        for i, case in enumerate(C.CASES):
            with st.container(border=True):
                st.markdown(f'<div class="tp-demo-title">{case["title"]}</div>'
                            f'<div class="tp-demo-text">{case["text"]}</div>', unsafe_allow_html=True)
                st.button("Open this case", key=f"case{i}", on_click=C.start_case, args=(case,), width="stretch")
        st.markdown('<p class="tp-note">Tip: ask a question on the first stage, click <b>Investigate</b> on any '
                    "suspect card, or pick your own place above.</p>", unsafe_allow_html=True)


def _selected_place() -> Place:
    """The place chosen in the builder (a built-in one, or a custom latitude/longitude)."""
    key = st.session_state["place"]
    if key != CUSTOM:
        return PLACES[key]
    lat, lon = float(st.session_state["clat"]), float(st.session_state["clon"])
    return Place(f"Custom ({lat:.2f}, {lon:.2f})", lat, lon, "Custom location",
                 "Your own spot. Each data cell is about 50 km wide, so this is a regional average.")


def render_case_builder() -> CaseContext:
    """Hero, place and year pickers, then load and scan the record. Stops the page if it cannot continue."""
    st.markdown(ui.hero(), unsafe_allow_html=True)
    with st.container(border=True):
        c1, c2 = st.columns([5, 6], gap="large")
        with c1:
            st.selectbox("Where do you want to investigate?", list(PLACES) + [CUSTOM], key="place",
                         format_func=lambda n: n if n == CUSTOM else f"{n}  ·  {PLACES[n].biome}")
            if st.session_state["place"] == CUSTOM:
                a, b = st.columns(2)
                a.number_input("Latitude", -90.0, 90.0, key="clat", step=0.5, format="%.2f")
                b.number_input("Longitude", -180.0, 180.0, key="clon", step=0.5, format="%.2f")
        with c2:
            st.slider("Which years?", FIRST_YEAR, LAST_YEAR, key="win",
                      help="Trends need a long record. Very short windows are dominated by natural ups and downs.")
            if st.session_state["win"] != (FIRST_YEAR, LAST_YEAR):
                st.button("Use the full record", on_click=C.reset_window, type="secondary")

    place = _selected_place()
    start, end = st.session_state["win"]
    if end - start < 9:
        st.warning("Pick at least 10 years. Shorter windows are mostly natural ups and downs, not trends.")
        st.stop()
    try:
        df = C.get_record(place.lat, place.lon)
    except (ClimateDataError, ValueError) as exc:
        st.error(f"Could not load the record for this place. {exc} Check your internet connection or choose one of "
                 "the built-in places, which are saved on this computer.")
        st.stop()
    results = C.get_scan(place.lat, place.lon, start, end)
    st.markdown(ui.case_strip(place.name, place.lat, place.lon, place.biome, place.blurb, start, end, len(results)),
                unsafe_allow_html=True)
    return CaseContext(place, start, end, df, results)
