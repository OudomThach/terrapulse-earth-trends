"""Stage 1 · Suspects: ask a question or scan all 20 variables, ranked by strength of evidence."""

from __future__ import annotations

import streamlit as st

from terrapulse import narrative as N, questions as Q, trends as T, ui
from terrapulse.case import CaseContext
from terrapulse.trends import TrendResult
from terrapulse.variables import GROUPS, VARIABLES

from . import common as C


def _summary_cards(ctx: CaseContext) -> None:
    """Four headline numbers for the whole scan."""
    usable = ctx.usable
    sig = [r for r in usable.values() if r.q < 0.05]
    clean = [r for r in sig if not r.suspicious_jump]
    jumps = [r for r in usable.values() if r.suspicious_jump]
    best = min(clean, key=lambda r: (r.q, -abs(r.z))) if clean else None
    cards = [ui.kpi("Variables tested", str(len(usable)), f"of {len(ctx.results)} available here"),
             ui.kpi("Significant trends", str(len(sig)), "after correcting for testing many variables at once")]
    if best:
        v = VARIABLES[best.code]
        cards.append(ui.kpi("Strongest clear signal", v.name, N.rate_text(v, best),
                            sub_tone="rise" if best.slope > 0 else "fall"))
    else:
        cards.append(ui.kpi("Strongest clear signal", "None", "no variable passed the test"))
    cards.append(ui.kpi("Possible data jumps", str(len(jumps)), "abrupt steps that may be data artefacts"))
    st.markdown(ui.kpi_row(cards), unsafe_allow_html=True)


def _card_grid(rows: list[TrendResult]) -> None:
    """Suspect cards, three per row, each with an Investigate button."""
    for i in range(0, len(rows), 3):
        cols = st.columns(3, gap="medium")
        for col, r in zip(cols, rows[i:i + 3]):
            with col, st.container(border=True):
                st.markdown(ui.suspect_card(VARIABLES[r.code], r, T.evidence_label(r.q), r.q), unsafe_allow_html=True)
                st.button("Investigate", key=f"inv_{r.code}", on_click=C.investigate, args=(r.code,), width="stretch")


def _ask_the_detective(ctx: CaseContext) -> list[str] | None:
    """Question pills and the detective's answer. Returns the clue codes to show, or None for 'all clues'."""
    st.markdown(ui.section("What are you curious about?",
                           "Pick a question and the detective answers it from the evidence, or scan everything."),
                unsafe_allow_html=True)
    options = [C.ALL_CLUES] + [q.text for q in Q.QUESTIONS] + [C.SURPRISE]
    choice = st.pills("Ask the detective", options, selection_mode="single", key="question",
                      label_visibility="collapsed") or C.ALL_CLUES
    if choice == C.ALL_CLUES:
        return None
    if choice == C.SURPRISE:
        codes = Q.surprise_me(ctx.results)
        lines = [f"{VARIABLES[c].name}: {N.rate_text(VARIABLES[c], ctx.results[c])}" for c in codes]
        st.markdown(ui.banner("Three clues worth a look", ui.md_bold_to_html(" · ".join(f"**{x}**" for x in lines)),
                              "sig", eyebrow="Detective's pick"), unsafe_allow_html=True)
        return codes
    question = Q.QUESTIONS_BY_TEXT[choice]
    ans = Q.answer(question, ctx.results)
    st.markdown(ui.banner(ans.headline, ui.md_bold_to_html(ans.body), ans.tone, eyebrow="Detective's answer"),
                unsafe_allow_html=True)
    st.caption(question.why)
    return ans.codes


def render(ctx: CaseContext) -> None:
    """Draw the summary, the question step and the ranked suspect board."""
    clue_codes = _ask_the_detective(ctx)
    if clue_codes is None:
        _summary_cards(ctx)          # scan-wide numbers only matter when looking at every clue

    if clue_codes is not None:
        st.markdown(ui.section("The clues behind the answer", "Strongest evidence first."), unsafe_allow_html=True)
        st.markdown(ui.direction_legend(), unsafe_allow_html=True)
        _card_grid([ctx.results[c] for c in clue_codes if ctx.results[c].usable])
    else:
        st.markdown(ui.section("The suspect board",
                               "Every variable ranked by strength of evidence. Open any card to see the full investigation."),
                    unsafe_allow_html=True)
        f1, f2 = st.columns([5, 2])
        with f1:
            groups = st.pills("Filter by type", GROUPS, selection_mode="multi", default=GROUPS, key="grp")
        with f2:
            only_sig = st.toggle("Only significant", value=False)
        st.markdown(ui.direction_legend(), unsafe_allow_html=True)
        ranked = sorted(ctx.usable.values(), key=lambda r: (r.q, -abs(r.z)))
        shown = [r for r in ranked if VARIABLES[r.code].group in (groups or GROUPS) and (not only_sig or r.q < 0.05)]
        if not shown:
            st.info("No variables match these filters. Try switching off 'Only significant'.")
        _card_grid(shown)
        untestable = [r for r in ctx.results.values() if not r.usable]
        if untestable:
            with st.expander(f"{len(untestable)} variable(s) could not be tested here"):
                for r in untestable:
                    st.markdown(f"**{VARIABLES[r.code].name}**: {r.reason}")

    st.download_button("Download this case file (Markdown)",
                       N.case_report_md(ctx.place.name, ctx.place.lat, ctx.place.lon, ctx.start, ctx.end, ctx.results),
                       file_name=f"case_file_{ctx.place.name.split(',')[0].replace(' ', '_').lower()}.md",
                       mime="text/markdown")
