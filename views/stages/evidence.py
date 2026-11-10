"""Stage 2 · Evidence: the full investigation of one variable (verdict, statistics, charts, caveats)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from terrapulse import charts, narrative as N, trends as T, ui
from terrapulse.case import CaseContext
from terrapulse.trends import TrendResult
from terrapulse.variables import CODES, VARIABLES, Variable

from . import common as C


def _verdict_banners(ctx: CaseContext, v: Variable, res: TrendResult) -> None:
    """Plain-language verdict, plus the data-jump caution (with a one-click re-test) when it applies."""
    verdict = N.verdict(v, res, ctx.place.name, ctx.start, ctx.end)
    tone, eyebrow = verdict["tone"], f"{verdict['label']} · {N.strength_dots(res.p)}"
    if res.suspicious_jump:   # don't present a possibly artificial trend as a clean win
        tone, eyebrow = "weak", eyebrow + " · read the caution below"
    st.markdown(ui.banner(verdict["headline"], ui.md_bold_to_html(verdict["body"]), tone, eyebrow=eyebrow),
                unsafe_allow_html=True)
    warn = N.jump_warning(v, res)
    if warn:
        st.markdown(ui.banner("Is this a real trend?", ui.md_bold_to_html(warn), "warn", eyebrow="Detective's caution"),
                    unsafe_allow_html=True)
        if res.jump_year + 9 <= ctx.end:
            st.button(f"Re-test from {res.jump_year} onward", on_click=C.retest_from, args=(res.jump_year, ctx.end),
                      type="primary")
        else:
            st.caption("Not enough years after the jump to re-test.")


def _statistic_cards(v: Variable, res: TrendResult) -> None:
    """Six numbers that justify the verdict."""
    d = v.decimals
    agree = (res.ols_p < 0.05) == (res.p < 0.05)
    pct = (f", {N.signed(res.pct_change, 0)}% of the average"
           if np.isfinite(res.pct_change) and abs(res.pct_change) < 1e4 else "")
    cards = [
        ui.kpi("Rate of change", N.rate_text(v, res), "Sen's slope: the median of all pairwise slopes",
               "rise" if res.slope > 0 else "fall"),
        ui.kpi("Total change", f"{N.signed(res.total_change, d)} {v.unit}", f"over {res.span_years:.0f} years{pct}"),
        ui.kpi("95% confidence range", f"{N.signed(res.ci_low * 10, d)} to {N.signed(res.ci_high * 10, d)}",
               "per decade. If it spans zero, the trend is not proven"),
        ui.kpi("Chance it is luck", "p < 0.001" if res.p < 0.001 else f"p = {res.p:.3f}", N.plain_p(res.p)),
        ui.kpi("Cross-check", f"{N.signed(res.ols_slope * 10, d)} per decade",
               ("Straight-line fit agrees" if agree else "Methods disagree: be careful") + f" (R² = {res.ols_r2:.2f})"),
        ui.kpi("Year-to-year memory", f"{res.lag1:+.2f}",
               "Adjusted for it so persistence cannot fake a trend" if res.inflation > 1 else "Low, so no adjustment needed"),
    ]
    st.markdown(ui.kpi_row(cards), unsafe_allow_html=True)


def _explainers(ctx: CaseContext, code: str, v: Variable, res: TrendResult, series: pd.Series) -> None:
    """Definition, chart-reading help and the data table (a text alternative to the charts)."""
    a, b, c = st.columns(3, gap="medium")
    with a, st.expander("What is this variable?"):
        st.markdown(f"**{v.name}** ({v.unit}). {v.definition}")
        st.markdown(f"*If it rises:* {v.rising_means}")
    with b, st.expander("How to read these charts"):
        st.markdown(
            "- **Trend line**: the steady rate of change that best fits the data.\n"
            "- **Orange band**: other trend lines that fit almost as well. If a flat line fits inside it, "
            "the trend is not proven.\n- **p-value**: how often luck alone would draw a pattern this strong. "
            "Below 0.05 is called significant.\n- **Colour** shows direction (red up, blue down), never good or bad.")
    with c, st.expander("View the data table"):
        tbl = pd.DataFrame({"year": res.years, f"yearly mean ({v.unit})": np.round(res.annual, 4),
                            f"trend line ({v.unit})": np.round(res.line_at(res.years + 0.5), 4)})
        st.dataframe(tbl, hide_index=True, width="stretch")
        monthly = pd.DataFrame({"value": series, "anomaly": T.monthly_anomalies(series)})
        monthly["12-month mean"] = series.rolling(12, min_periods=9, center=True).mean()
        st.download_button("Download monthly data (CSV)", monthly.round(5).to_csv(),
                           file_name=f"{code}_{ctx.place.name.split(',')[0]}.csv", mime="text/csv")


def render(ctx: CaseContext) -> None:
    """Draw the evidence stage for the selected variable."""
    st.selectbox("Which clue are you testing?", CODES, key="var",
                 format_func=lambda c: f"{VARIABLES[c].name}  ·  {VARIABLES[c].group}")
    code = st.session_state["var"]
    v, res = VARIABLES[code], ctx.results[code]
    if not res.usable:
        st.info(f"**{v.name}** cannot be tested here. {res.reason}")
        return
    _verdict_banners(ctx, v, res)
    _statistic_cards(v, res)

    st.markdown(ui.section("The full record", "Every month in the window, with the trend and how sure we are of it."),
                unsafe_allow_html=True)
    mode = st.radio("Show", ["Seasons removed", "Real values"], horizontal=True, label_visibility="collapsed",
                    help="'Seasons removed' subtracts each calendar month's long-term average so only the "
                         "unusual part is left.")
    series = ctx.window_series(code)
    C.show(charts.trend_figure(series, res, v, anomalies=(mode == "Seasons removed")), key="trend")
    st.caption("Grey: each month. Blue: 12-month average, which smooths out the seasons. Orange: the trend. "
               "The orange band is the 95% range of plausible trend lines.")

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(ui.section("Year by year", "These yearly averages are what the statistical test actually uses."),
                    unsafe_allow_html=True)
        C.show(charts.annual_figure(res, v), key="annual")
    with right:
        st.markdown(ui.section("Which seasons drive it?",
                               "Rate of change for each calendar month on its own. Solid bars are significant."),
                    unsafe_allow_html=True)
        C.show(charts.seasonal_figure(T.seasonal_fingerprint(ctx.df[code], ctx.start, ctx.end), v), key="season")

    _explainers(ctx, code, v, res, series)
    extra_years = T.years_to_significance(res)
    if res.p >= 0.05 and extra_years:
        st.info(f"**What would it take?** At the current rate and noise, about **{extra_years} more years** of data "
                "would turn this from 'not proven' into significant. Short records often just need more time.")
