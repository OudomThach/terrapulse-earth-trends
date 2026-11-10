"""Stage 4 · Connections: what the significant trends say together, and which variables move together."""

from __future__ import annotations

import streamlit as st

from terrapulse import charts, narrative as N, ui
from terrapulse.case import CaseContext
from terrapulse.variables import VARIABLES

from . import common as C


def _link_card(link: dict) -> None:
    """One explained relationship, marked ✓ when it matches known physics and ⚠ when it does not."""
    a, b = VARIABLES[link["a"]], VARIABLES[link["b"]]
    sign = "move together" if link["rho"] > 0 else "move in opposite directions"
    mark = "" if link["matches"] is None else ("✓ " if link["matches"] else "⚠ ")
    note = f"\n\n{mark}{link['note']}" if link["note"] else ""
    with st.container(border=True):
        st.markdown(f"**{a.name}** and **{b.name}** {sign} ({link['rho']:+.2f}).{note}")


def render(ctx: CaseContext) -> None:
    """Draw the story cards, the link heatmap and the explained relationships."""
    story = N.earth_story(ctx.results)
    st.markdown(ui.section("What the significant trends say together",
                           "Individual trends become a story when they agree with the physics. These readings are "
                           "'consistent with', not proof of cause."), unsafe_allow_html=True)
    if story:
        st.markdown(ui.story_cards(story), unsafe_allow_html=True)
    else:
        st.info("No clear multi-variable story here: few variables passed the significance test. "
                "Try a longer window or a different place.")

    corr = C.get_corr(ctx.place.lat, ctx.place.lon, ctx.start, ctx.end)
    st.markdown(ui.section("How the variables move together",
                           "Month-to-month wiggles with the seasons and long-term trends removed, so these links are "
                           "not just two trends that happen to coincide."), unsafe_allow_html=True)
    left, right = st.columns([3, 2], gap="large")
    with left:
        C.show(charts.correlation_figure(corr), key="corr")
        st.caption("Red: when one is above normal, the other tends to be too. Blue: when one is high, the other tends "
                   "to be low. Grey: little link.")
    with right:
        st.markdown("**Strongest explainable links**")
        links = N.top_connections(corr, k=7)
        if not links:
            st.caption("No strong links found.")
        for link in links:
            _link_card(link)
    st.markdown('<p class="tp-note">Correlation shows that two things move together, not that one causes the other. '
                "The explanations marked ✓ are well-understood physical links; ⚠ marks a relationship that is "
                "the opposite of the usual expectation here.</p>", unsafe_allow_html=True)
