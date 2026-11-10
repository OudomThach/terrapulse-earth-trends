"""Trend Detective page: pick a place, ask a question or scan 20 Earth-system variables, and test each
trend for statistical significance.

This file only wires the page together; the work lives in ``views/stages/*`` (one module per stage) and
in the Streamlit-free ``terrapulse`` package (data, statistics, explanations, charts).
"""

from __future__ import annotations

import streamlit as st

from terrapulse.climate import CUSTOM
from views.stages import builder, common as C, evidence, how, links, suspects, world

RENDERERS = {C.S_SUSPECTS: suspects.render, C.S_EVIDENCE: evidence.render, C.S_WHERE: world.render,
             C.S_LINKS: links.render, C.S_HOW: how.render}

C.init_state()
builder.render_sidebar()
ctx = builder.render_case_builder()

st.segmented_control("Stage", C.STAGES, key="stage", label_visibility="collapsed")
stage = st.session_state.get("stage") or C.S_SUSPECTS

if st.session_state["place"] != CUSTOM:
    # keep the address bar a shareable link to exactly this view
    params = {"place": st.session_state["place"], "stage": str(C.STAGES.index(stage) + 1), "var": st.session_state["var"],
              "from": str(ctx.start), "to": str(ctx.end)}
    q = C.question_param(st.session_state.get("question"))
    if q:
        params["q"] = q
    st.query_params.from_dict(params)

RENDERERS[stage](ctx)
