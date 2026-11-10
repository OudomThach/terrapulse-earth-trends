import numpy as np
import pandas as pd
import pytest
from scipy import stats

from terrapulse import trends as T
from terrapulse.climate import parse_monthly


def monthly(values_by_year, seasonal=None, start_year=1990):
    """Build a monthly series from per-year levels plus an optional 12-value seasonal cycle."""
    seasonal = np.zeros(12) if seasonal is None else np.asarray(seasonal)
    idx = pd.date_range(f"{start_year}-01-01", periods=12 * len(values_by_year), freq="MS")
    vals = np.repeat(values_by_year, 12) + np.tile(seasonal, len(values_by_year))
    return pd.Series(vals, index=idx)


# ------------------------------------------------------------------ Mann-Kendall
def test_mk_perfect_increase():
    r = T.mann_kendall(np.arange(20.0))
    assert r["S"] == 20 * 19 / 2
    assert r["tau"] == pytest.approx(1.0)
    assert r["p"] < 1e-5


def test_mk_perfect_decrease_is_symmetric():
    up, down = T.mann_kendall(np.arange(15.0)), T.mann_kendall(-np.arange(15.0))
    assert down["S"] == -up["S"] and down["z"] == pytest.approx(-up["z"]) and down["p"] == pytest.approx(up["p"])


def test_mk_matches_scipy_kendall_tau():
    rng = np.random.default_rng(1)
    x = np.cumsum(rng.normal(size=30)) + 0.1 * np.arange(30)
    mk = T.mann_kendall(x)
    ref = stats.kendalltau(np.arange(30), x)
    assert mk["tau"] == pytest.approx(ref.statistic, abs=1e-9)
    assert mk["p"] == pytest.approx(ref.pvalue, abs=0.02)   # normal approx vs exact


def test_mk_ties_handled_and_constant_series():
    assert T.mann_kendall(np.ones(12))["p"] == 1.0
    r = T.mann_kendall(np.array([1, 1, 2, 2, 3, 3, 4, 4.0]))
    assert 0 < r["p"] < 0.05


def test_mk_variance_inflation_makes_test_more_conservative():
    x = np.arange(25.0) + np.random.default_rng(0).normal(0, 3, 25)
    assert T.mann_kendall(x, var_inflation=2.0)["p"] > T.mann_kendall(x)["p"]


# ------------------------------------------------------------------ Sen slope and CI
def test_sen_slope_recovers_known_slope():
    t = np.arange(1990, 2026, dtype=float)
    x = 0.03 * (t - 1990) + np.random.default_rng(2).normal(0, 0.1, len(t))
    slope, lo, hi = T.sen_slope(t, x, T.mann_kendall(x)["var"])
    assert slope == pytest.approx(0.03, abs=0.006)
    assert lo < slope < hi


def test_sen_slope_ignores_outlier():
    t = np.arange(20.0)
    x = 2.0 * t
    x[10] = 500.0
    assert T.sen_slope(t, x, T.mann_kendall(x)["var"])[0] == pytest.approx(2.0, abs=0.1)


def test_sen_ci_coverage_is_reasonable():
    rng = np.random.default_rng(3)
    t = np.arange(1990, 2026, dtype=float)
    hits = 0
    for _ in range(200):
        x = 0.02 * (t - 1990) + rng.normal(0, 0.3, len(t))
        _, lo, hi = T.sen_slope(t, x, T.mann_kendall(x)["var"])
        hits += lo <= 0.02 <= hi
    assert hits / 200 > 0.90


# ------------------------------------------------------------------ error rates (the science check)
def test_false_positive_rate_without_trend_is_about_5_percent():
    rng = np.random.default_rng(4)
    hits = sum(T.analyze(monthly(rng.normal(0, 1, 36))).p < 0.05 for _ in range(400))
    assert 0.02 < hits / 400 < 0.09


def test_autocorrelated_noise_does_not_inflate_false_positives_much():
    rng = np.random.default_rng(5)
    hits, n_sims = 0, 400
    for _ in range(n_sims):
        e = rng.normal(0, 1, 36)
        x = np.zeros(36)
        for i in range(1, 36):
            x[i] = 0.6 * x[i - 1] + e[i]
        hits += T.analyze(monthly(x)).p < 0.05
    assert hits / n_sims < 0.13


def test_real_trend_is_detected():
    rng = np.random.default_rng(6)
    hits = sum(T.analyze(monthly(0.05 * np.arange(36) + rng.normal(0, 0.5, 36))).p < 0.05 for _ in range(100))
    assert hits >= 95


# ------------------------------------------------------------------ analyze()
def test_strong_seasonal_cycle_does_not_create_a_trend():
    season = 15 * np.sin(np.linspace(0, 2 * np.pi, 12, endpoint=False))
    rng = np.random.default_rng(7)
    res = T.analyze(monthly(rng.normal(0, 0.2, 36), seasonal=season))
    assert res.usable and res.p > 0.05


def test_seasonal_cycle_does_not_hide_a_trend():
    season = 15 * np.sin(np.linspace(0, 2 * np.pi, 12, endpoint=False))
    res = T.analyze(monthly(0.04 * np.arange(36), seasonal=season))
    assert res.slope == pytest.approx(0.04, abs=1e-6) and res.p < 0.001
    assert res.direction == "rising" and res.per_decade == pytest.approx(0.4)
    assert res.total_change == pytest.approx(0.04 * 36)


def test_analyze_respects_window_and_flags_short_or_flat_series():
    s = monthly(0.05 * np.arange(36))
    assert T.analyze(s, start=2010, end=2025).years[0] == 2010
    assert not T.analyze(s, start=2020, end=2025).usable
    flat = T.analyze(monthly(np.zeros(36)))
    assert not flat.usable and "nothing to test" in flat.reason


def test_incomplete_years_are_dropped():
    s = monthly(np.arange(12.0))
    s.iloc[: 12 * 3 + 6] = np.nan        # first 3 years empty, 4th has only 6 months
    ann = T.annual_means(s.dropna())
    assert np.isnan(ann.loc[1993]) and ann.loc[1994] == 4.0


def test_ols_and_sen_agree_on_clean_data():
    res = T.analyze(monthly(0.03 * np.arange(36) + np.random.default_rng(8).normal(0, 0.05, 36)))
    assert res.ols_slope == pytest.approx(res.slope, abs=0.005)
    assert res.ols_low < res.ols_slope < res.ols_high and 0 <= res.ols_r2 <= 1


def test_trend_line_passes_through_anchor_and_ci_wedge_brackets_slope():
    res = T.analyze(monthly(0.03 * np.arange(36) + np.random.default_rng(9).normal(0, 0.2, 36)))
    assert res.line_at(res.anchor_t) == pytest.approx(res.anchor_y)
    assert res.ci_low <= res.slope <= res.ci_high


# ------------------------------------------------------------------ multiple testing & helpers
def test_benjamini_hochberg_known_values():
    q = T.benjamini_hochberg(np.array([0.01, 0.04, 0.03, 0.20]))
    assert q == pytest.approx([0.04, 0.0533333, 0.0533333, 0.20], abs=1e-6)
    assert (q >= np.array([0.01, 0.04, 0.03, 0.20])).all()


def test_scan_adds_q_values_never_below_p():
    rng = np.random.default_rng(10)
    df = pd.DataFrame({f"v{i}": monthly(rng.normal(0, 1, 36) + (0.1 * np.arange(36) if i < 2 else 0)) for i in range(6)})
    out = T.scan(df, list(df))
    assert all(r.q >= r.p - 1e-12 for r in out.values())
    assert out["v0"].q < 0.05


def test_evidence_labels():
    assert [T.evidence_label(p) for p in (0.001, 0.03, 0.08, 0.4)] == [
        "Strong evidence", "Significant", "Weak hint", "No clear trend"]


def test_years_to_significance():
    rng = np.random.default_rng(11)
    sig = T.analyze(monthly(0.1 * np.arange(36) + rng.normal(0, 0.3, 36)))
    assert T.years_to_significance(sig) == 0
    weak = None
    for seed in range(100, 200):          # find a genuinely not-yet-significant but leaning series
        cand = T.analyze(monthly(0.012 * np.arange(36) + np.random.default_rng(seed).normal(0, 0.5, 36)))
        if 0.10 < cand.p < 0.4:
            weak = cand
            break
    assert weak is not None
    extra = T.years_to_significance(weak)
    assert extra is None or extra > 0
    # a flat series with pure noise should never promise significance soon
    flat = T.analyze(monthly(np.random.default_rng(1).normal(0, 1, 36)))
    assert T.years_to_significance(flat) in (None,) or T.years_to_significance(flat) > 0 or flat.p < 0.05


def test_seasonal_fingerprint_finds_the_warming_month():
    rng = np.random.default_rng(12)
    vals = rng.normal(0, 0.2, (36, 12))
    vals[:, 6] += 0.08 * np.arange(36)         # only July trends
    s = pd.Series(vals.ravel(), index=pd.date_range("1990-01-01", periods=432, freq="MS"))
    fp = T.seasonal_fingerprint(s)
    assert fp.loc[6, "p"] < 0.001 and fp.loc[6, "per_decade"] == pytest.approx(0.8, abs=0.1)
    assert (fp.drop(6)["p"] > 0.001).all()


def test_correlations_detect_linked_variables_after_detrending():
    rng = np.random.default_rng(13)
    idx = pd.date_range("1990-01-01", periods=432, freq="MS")
    a = pd.Series(rng.normal(size=432) + np.linspace(0, 5, 432), index=idx)
    df = pd.DataFrame({"a": a, "b": a * -0.8 + rng.normal(0, 0.3, 432), "c": rng.normal(size=432)})
    c = T.detrended_anomaly_correlations(df, ["a", "b", "c"])
    assert c.loc["a", "b"] < -0.7 and abs(c.loc["a", "c"]) < 0.2


def test_parse_monthly_drops_annual_rows_and_fill_values():
    payload = {"properties": {"parameter": {"T2M": {"199001": 1.0, "199002": -999.0, "199013": 9.9, "199101": 2.0}}}}
    df = parse_monthly(payload)
    assert len(df) == 3 and df["T2M"].isna().sum() == 1 and 9.9 not in df["T2M"].values


# ------------------------------------------------------------------ step-change check
def test_pettitt_finds_the_jump_year():
    rng = np.random.default_rng(20)
    x = np.concatenate([rng.normal(0, 0.3, 11), rng.normal(3, 0.3, 25)])   # jump after 2000
    r = T.pettitt(x)
    assert r["index"] == 11 and r["p"] < 0.001
    assert r["after"] - r["before"] == pytest.approx(3, abs=0.5)


def test_pettitt_false_alarm_rate_on_noise_is_low():
    rng = np.random.default_rng(21)
    hits = sum(T.pettitt(rng.normal(size=36))["p"] < 0.01 for _ in range(400))
    assert hits / 400 < 0.03


def test_analyze_flags_an_abrupt_jump_but_not_a_steady_slope():
    rng = np.random.default_rng(22)
    jump = T.analyze(monthly(np.concatenate([rng.normal(40, 2, 11), rng.normal(66, 2, 25)])))
    assert jump.suspicious_jump and jump.jump_year == 2001
    false_flags = sum(T.analyze(monthly(0.05 * np.arange(36) + np.random.default_rng(s).normal(0, 0.15, 36))).suspicious_jump
                      for s in range(100))
    assert false_flags <= 3          # steady slopes must almost never be called jumps


# ------------------------------------------------------------------ missing data
def test_parse_monthly_keeps_every_catalogued_variable():
    from terrapulse.variables import CODES
    payload = {"properties": {"parameter": {"T2M": {"199001": 1.0, "199002": 2.0},
                                            "SNODP": {"199001": -999.0, "199002": -999.0}}}}
    df = parse_monthly(payload)
    assert list(df.columns) == CODES and df["SNODP"].isna().all() and df["TO3"].isna().all()


def test_analyze_handles_a_variable_with_no_data():
    empty = pd.Series(np.nan, index=pd.date_range("1990-01-01", periods=432, freq="MS"))
    res = T.analyze(empty, "SNODP")
    assert not res.usable and "no record" in res.reason
