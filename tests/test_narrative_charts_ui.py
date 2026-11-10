import numpy as np
import pandas as pd
import pytest

from terrapulse import charts, narrative as N, trends as T, ui
from terrapulse.climate import PLACES, load_monthly
from terrapulse.variables import CODES, GROUPS, VARIABLES


def make_series(levels, start=1990):
    idx = pd.date_range(f"{start}-01-01", periods=12 * len(levels), freq="MS")
    return pd.Series(np.repeat(levels, 12) + np.tile(np.sin(np.arange(12)), len(levels)), index=idx)


@pytest.fixture(scope="module")
def warming():
    rng = np.random.default_rng(1)
    s = make_series(0.05 * np.arange(36) + rng.normal(0, 0.2, 36))
    return s, T.analyze(s, "T2M")


# ------------------------------------------------------------------ catalog
def test_catalog_is_complete_and_consistent():
    assert len(CODES) == 20 and len(set(CODES)) == 20
    assert {v.group for v in VARIABLES.values()} == set(GROUPS)
    assert all(v.definition and v.unit and v.rising_means for v in VARIABLES.values())


# ------------------------------------------------------------------ narrative
def test_signed_and_plain_p():
    assert N.signed(1.234, 2) == "+1.23" and N.signed(-0.5, 1) == "−0.5" and N.signed(float("nan")) == "n/a"
    assert N.plain_p(0.0004) == "less than 1 time in 1,000"
    assert N.plain_p(0.03) == "about 3 times in 100"
    assert N.strength_dots(0.001) == "●●●" and N.strength_dots(0.5) == "○○○"


def test_verdict_tones(warming):
    _, res = warming
    v = N.verdict(VARIABLES["T2M"], res, "Testville", 1990, 2025)
    assert v["tone"] == "strong" and "rising" in v["headline"] and "Testville" in v["body"]
    flat = T.analyze(make_series(np.random.default_rng(3).normal(0, 1, 36)), "T2M")
    assert N.verdict(VARIABLES["T2M"], flat, "x", 1990, 2025)["tone"] in ("none", "weak")
    bad = T.TrendResult("SNODP", False, "nothing here")
    assert N.verdict(VARIABLES["SNODP"], bad, "x", 1990, 2025)["label"] == "Not testable"


def test_jump_warning_only_when_flagged():
    rng = np.random.default_rng(4)
    jump = T.analyze(make_series(np.r_[rng.normal(40, 2, 11), rng.normal(66, 2, 25)]), "CLOUD_AMT")
    assert "2001" in N.jump_warning(VARIABLES["CLOUD_AMT"], jump)
    steady = T.analyze(make_series(0.05 * np.arange(36) + rng.normal(0, 0.05, 36)), "T2M")
    assert N.jump_warning(VARIABLES["T2M"], steady) is None


def test_connections_exclude_trivial_pairs_and_explain_known_links():
    cols = ["T2M", "T2M_MAX", "QV2M", "RH2M"]
    corr = pd.DataFrame(np.eye(4), index=cols, columns=cols)
    corr.loc["T2M", "T2M_MAX"] = corr.loc["T2M_MAX", "T2M"] = 0.99      # same family: must be skipped
    corr.loc["T2M", "RH2M"] = corr.loc["RH2M", "T2M"] = -0.7           # expected negative link
    corr.loc["T2M", "QV2M"] = corr.loc["QV2M", "T2M"] = -0.5           # opposite of expectation
    links = N.top_connections(corr)
    pairs = {frozenset({l["a"], l["b"]}) for l in links}
    assert frozenset({"T2M", "T2M_MAX"}) not in pairs
    by_pair = {frozenset({l["a"], l["b"]}): l for l in links}
    assert by_pair[frozenset({"T2M", "RH2M"})]["matches"] is True
    assert by_pair[frozenset({"T2M", "QV2M"})]["matches"] is False and "Unexpected" in by_pair[frozenset({"T2M", "QV2M"})]["note"]


def test_earth_story_is_driven_by_significant_results_only():
    mk = lambda code, slope, q=0.001: T.TrendResult(code, True, slope=slope, p=q, q=q, mean=1.0,
                                                     years=np.arange(1990, 2026), annual=np.zeros(36))
    results = {"T2M": mk("T2M", 0.05), "T2M_MIN": mk("T2M_MIN", 0.09), "T2M_MAX": mk("T2M_MAX", 0.03),
               "QV2M": mk("QV2M", 0.01), "GWETROOT": mk("GWETROOT", -0.002, q=0.4)}
    titles = [s["title"] for s in N.earth_story(results)]
    assert "The place is warming" in titles and "Nights are warming faster than days" in titles
    assert "More water vapour in warmer air" in titles
    assert not any("soil" in t.lower() for t in titles)             # not significant: no claim
    assert all(s["text"][0].isupper() for s in N.earth_story(results))


def test_case_report_lists_every_testable_variable():
    p = PLACES["Svalbard, Arctic"]
    df = load_monthly(p.lat, p.lon)
    res = T.scan(df, CODES, 1990, 2025)
    md = N.case_report_md(p.name, p.lat, p.lon, 1990, 2025, res)
    assert md.startswith("# Trend Detective case file") and md.count("\n| ") >= len([r for r in res.values() if r.usable])


# ------------------------------------------------------------------ charts
def test_chart_builders_produce_valid_figures(warming):
    s, res = warming
    v = VARIABLES["T2M"]
    for anomalies in (False, True):
        assert len(charts.trend_figure(s, res, v, anomalies).data) == 4
    assert len(charts.annual_figure(res, v).data) == 3
    fp = T.seasonal_fingerprint(s)
    assert list(charts.seasonal_figure(fp, v).data[0].x) == charts.MONTHS
    df = pd.DataFrame({"name": ["A", "B"], "lat": [0, 10], "lon": [0, 10], "biome": ["x", "y"],
                       "per_decade": [0.5, -0.4], "p": [0.01, 0.6], "significant": [True, False]})
    assert len(charts.map_figure(df, v).data) >= 2
    assert len(charts.map_figure(df, v, satellite=False).layout.map.layers) == 0
    assert len(charts.trend_bars_figure(df, v).data) == 1


def test_charts_show_no_colour_only_meaning_and_flag_jumps():
    rng = np.random.default_rng(5)
    s = make_series(np.r_[rng.normal(40, 2, 11), rng.normal(66, 2, 25)])
    res = T.analyze(s, "CLOUD_AMT")
    fig = charts.trend_figure(s, res, VARIABLES["CLOUD_AMT"])
    assert any("data jump" in (a.text or "") for a in fig.layout.annotations)


# ------------------------------------------------------------------ ui html
def test_ui_components_escape_text_and_carry_meaning_without_colour(warming):
    _, res = warming
    html = ui.suspect_card(VARIABLES["T2M"], res, "Strong evidence", 0.001)
    assert "&#9650;" in html and "Strong evidence" in html and "●●●" in html     # arrow + words + dots
    assert "<script" not in ui.case_strip("<script>x</script>", 0, 0, "b", "c", 1990, 2025, 20)
    assert "<b>bold</b>" in ui.md_bold_to_html("a **bold** b") and "&lt;i&gt;" in ui.md_bold_to_html("<i>")
    assert ui.sparkline([1], "rise") == "" and "<polyline" in ui.sparkline([1, 2, 3], "rise")


def test_unusable_card_explains_why():
    html = ui.suspect_card(VARIABLES["SNODP"], T.TrendResult("SNODP", False, "The value never changes here."),
                           "Not testable", 1.0)
    assert "never changes" in html
