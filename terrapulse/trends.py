"""Trend statistics for monthly Earth-system records.

Method (kept deliberately classic so it can be explained and checked):
  1. Average each calendar year (needs >= 9 valid months). Averaging whole years removes the
     seasonal cycle, so a cold winter next to a warm summer cannot masquerade as a trend.
  2. Mann-Kendall test on the annual means: is there a monotonic rise or fall? (non-parametric,
     no assumption that the data are bell-shaped). Variance is inflated when year-to-year
     autocorrelation is itself detectable, so persistence cannot fake significance.
  3. Sen's slope: the median of all pairwise slopes - the rate of change, robust to outliers -
     with a 95% confidence interval from the Mann-Kendall variance (Gilbert 1987).
  4. Cross-check with ordinary least squares and its 95% confidence interval.
  5. When many variables are tested at once, p-values are adjusted with Benjamini-Hochberg so
     "significant" results are not just the lucky ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

MIN_MONTHS_PER_YEAR = 9
MIN_YEARS = 8


# --------------------------------------------------------------------------- building blocks
def annual_means(series: pd.Series, min_months: int = MIN_MONTHS_PER_YEAR) -> pd.Series:
    """Calendar-year means; years with fewer than ``min_months`` valid months become NaN."""
    g = series.groupby(series.index.year)
    out = g.mean()
    out[g.count() < min_months] = np.nan
    return out


def monthly_anomalies(series: pd.Series) -> pd.Series:
    """Each month minus the long-term average for that calendar month (removes the seasons)."""
    clim = series.groupby(series.index.month).transform("mean")
    return series - clim


def mann_kendall(x: np.ndarray, var_inflation: float = 1.0) -> dict:
    """Mann-Kendall test for a monotonic trend. ``x`` must be time-ordered with no NaN."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 3:
        return {"S": 0.0, "var": 0.0, "z": 0.0, "p": 1.0, "tau": 0.0, "n": n}
    diff = np.sign(x[None, :] - x[:, None])          # entry [i, j] = sign(x_j - x_i)
    s = float(np.triu(diff, k=1).sum())
    _, counts = np.unique(x, return_counts=True)
    ties = float(np.sum(counts * (counts - 1) * (2 * counts + 5)))
    var = (n * (n - 1) * (2 * n + 5) - ties) / 18.0 * var_inflation
    if var <= 0:
        z = 0.0
    else:
        z = (s - np.sign(s)) / np.sqrt(var)           # continuity correction
    p = float(2 * (1 - stats.norm.cdf(abs(z))))
    tau = s / (n * (n - 1) / 2)
    return {"S": s, "var": var, "z": float(z), "p": p, "tau": float(tau), "n": n}


def sen_slope(t: np.ndarray, x: np.ndarray, var: float, alpha: float = 0.05):
    """Theil-Sen slope and its (1-alpha) confidence interval."""
    i, j = np.triu_indices(len(x), k=1)
    dt = t[j] - t[i]
    keep = dt != 0
    slopes = np.sort((x[j] - x[i])[keep] / dt[keep])
    n_pairs = len(slopes)
    if n_pairs == 0:
        return 0.0, 0.0, 0.0
    med = float(np.median(slopes))
    c = stats.norm.ppf(1 - alpha / 2) * np.sqrt(max(var, 0.0))
    lo_idx = np.clip((n_pairs - c) / 2 - 1, 0, n_pairs - 1)
    hi_idx = np.clip((n_pairs + c) / 2, 0, n_pairs - 1)
    grid = np.arange(n_pairs)
    return med, float(np.interp(lo_idx, grid, slopes)), float(np.interp(hi_idx, grid, slopes))


def pettitt(x: np.ndarray) -> dict:
    """Pettitt test for ONE abrupt change point. Returns the index of the first value after the
    jump, the approximate p-value, and the mean before/after."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 6:
        return {"index": None, "p": 1.0, "before": np.nan, "after": np.nan}
    d = np.sign(x[None, :] - x[:, None])
    u = np.array([d[: t + 1, t + 1:].sum() for t in range(n - 1)])
    k = float(np.max(np.abs(u)))
    t_star = int(np.argmax(np.abs(u)))
    p = float(min(1.0, 2 * np.exp(-6 * k ** 2 / (n ** 3 + n ** 2))))
    return {"index": t_star + 1, "p": p, "before": float(np.mean(x[: t_star + 1])),
            "after": float(np.mean(x[t_star + 1:]))}


def lag1_autocorr(resid: np.ndarray) -> float:
    """Correlation of a series with itself one step later (its 'memory')."""
    r = np.asarray(resid, dtype=float)
    if len(r) < 4 or np.allclose(r, r[0]):
        return 0.0
    r = r - r.mean()
    denom = float(np.sum(r * r))
    return float(np.sum(r[1:] * r[:-1]) / denom) if denom > 0 else 0.0


def benjamini_hochberg(p: np.ndarray) -> np.ndarray:
    """False-discovery-rate adjusted p-values (q-values)."""
    p = np.asarray(p, dtype=float)
    n = len(p)
    if n == 0:
        return p
    order = np.argsort(p)
    ranked = p[order] * n / (np.arange(n) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    q = np.empty(n)
    q[order] = np.clip(ranked, 0, 1)
    return q


def evidence_label(p: float) -> str:
    """Strong evidence / Significant / Weak hint / No clear trend, from a p-value."""
    if p < 0.01:
        return "Strong evidence"
    if p < 0.05:
        return "Significant"
    if p < 0.10:
        return "Weak hint"
    return "No clear trend"


# --------------------------------------------------------------------------- one variable
@dataclass
class TrendResult:
    """Everything we learn about one variable's trend (rate, confidence range, tests, jump check)."""

    code: str
    usable: bool
    reason: str = ""
    years: np.ndarray = field(default_factory=lambda: np.array([]))
    annual: np.ndarray = field(default_factory=lambda: np.array([]))
    mean: float = np.nan
    slope: float = np.nan            # Sen slope, units per YEAR
    ci_low: float = np.nan
    ci_high: float = np.nan
    p: float = np.nan                # Mann-Kendall p (after autocorrelation adjustment)
    z: float = np.nan
    tau: float = np.nan
    lag1: float = 0.0
    inflation: float = 1.0
    ols_slope: float = np.nan
    ols_low: float = np.nan
    ols_high: float = np.nan
    ols_r2: float = np.nan
    ols_p: float = np.nan
    anchor_t: float = np.nan         # trend line passes through (anchor_t, anchor_y)
    anchor_y: float = np.nan
    q: float = np.nan                # filled in by scan() after multiple-test correction
    jump_year: int | None = None     # first year of the "after" regime, if an abrupt jump is likely
    jump_p: float = 1.0
    jump_before: float = np.nan
    jump_after: float = np.nan
    jump_fit_ratio: float = np.nan   # error of a one-step fit / error of a straight-line fit (<1 = step fits better)

    @property
    def suspicious_jump(self) -> bool:
        """One sudden step that fits the record clearly better than a slope is often a change in
        instruments or data processing rather than climate. (Pettitt alone also fires on steady
        slopes, so the step must also beat a straight line.)"""
        return (self.usable and self.jump_year is not None and self.jump_p < 0.01
                and self.jump_fit_ratio < 0.7)

    @property
    def per_decade(self) -> float:
        """Rate of change per decade (Sen's slope times ten)."""
        return self.slope * 10

    @property
    def span_years(self) -> float:
        """Number of calendar years the test covers."""
        return float(self.years[-1] - self.years[0] + 1) if len(self.years) else 0.0

    @property
    def total_change(self) -> float:
        """Rate multiplied by the span: the overall change across the window."""
        return self.slope * self.span_years

    @property
    def pct_change(self) -> float:
        """Total change as a percentage of the average level (NaN if the average is zero)."""
        if not self.usable or not abs(self.mean) > 1e-12:
            return np.nan
        return 100 * self.total_change / abs(self.mean)

    @property
    def direction(self) -> str:
        """'rising', 'falling' or 'flat'."""
        if not self.usable or self.slope == 0:
            return "flat"
        return "rising" if self.slope > 0 else "falling"

    @property
    def ci_excludes_zero(self) -> bool:
        """True if the 95% confidence range does not include zero."""
        return self.ci_low > 0 or self.ci_high < 0

    def line_at(self, t: np.ndarray | float, slope: float | None = None):
        """Height of the trend line at time(s) ``t``; ``slope`` lets callers draw the uncertainty wedge."""
        s = self.slope if slope is None else slope
        return self.anchor_y + s * (np.asarray(t) - self.anchor_t)


def analyze(series: pd.Series, code: str = "", start: int | None = None, end: int | None = None) -> TrendResult:
    """Full trend analysis of one monthly series over [start, end] (calendar years)."""
    s = series.dropna()
    if start is not None:
        s = s[s.index.year >= start]
    if end is not None:
        s = s[s.index.year <= end]
    if s.empty:
        return TrendResult(code, False, "There is no record of this variable at this location.")
    ann = annual_means(s).dropna()
    if len(ann) < MIN_YEARS:
        return TrendResult(code, False, f"Only {len(ann)} usable years (need {MIN_YEARS}).")
    t = ann.index.to_numpy(dtype=float) + 0.5          # mid-year
    x = ann.to_numpy(dtype=float)
    if np.ptp(x) < 1e-9 or np.std(x) < 1e-9:
        return TrendResult(code, False, "The value never changes here, so there is nothing to test.")

    base = mann_kendall(x)
    slope0, _, _ = sen_slope(t, x, base["var"])
    resid = x - (slope0 * t + np.median(x - slope0 * t))
    r1 = lag1_autocorr(resid)
    infl = 1.0
    if r1 > 1.645 / np.sqrt(len(x)):                   # only when persistence is itself detectable
        infl = float(np.clip((1 + r1) / (1 - r1), 1.0, 4.0))
    mk = mann_kendall(x, var_inflation=infl)
    slope, lo, hi = sen_slope(t, x, mk["var"])

    ols = stats.linregress(t, x)
    tcrit = stats.t.ppf(0.975, len(x) - 2)
    anchor_t = float(np.median(t))
    anchor_y = float(np.median(x - slope * t) + slope * anchor_t)
    pt = pettitt(x)
    ratio = np.nan
    if pt["index"] is not None:
        k = pt["index"]
        sse_step = float(np.sum((x[:k] - x[:k].mean()) ** 2) + np.sum((x[k:] - x[k:].mean()) ** 2))
        sse_line = float(np.sum((x - (ols.intercept + ols.slope * t)) ** 2))
        ratio = sse_step / sse_line if sse_line > 0 else np.nan
    return TrendResult(
        jump_year=int(ann.index[pt["index"]]) if pt["index"] is not None else None,
        jump_p=pt["p"], jump_before=pt["before"], jump_after=pt["after"], jump_fit_ratio=ratio,
        code=code, usable=True, years=ann.index.to_numpy(), annual=x, mean=float(np.mean(x)),
        slope=slope, ci_low=lo, ci_high=hi, p=mk["p"], z=mk["z"], tau=mk["tau"], lag1=r1, inflation=infl,
        ols_slope=float(ols.slope), ols_low=float(ols.slope - tcrit * ols.stderr),
        ols_high=float(ols.slope + tcrit * ols.stderr), ols_r2=float(ols.rvalue ** 2), ols_p=float(ols.pvalue),
        anchor_t=anchor_t, anchor_y=anchor_y)


def scan(df: pd.DataFrame, codes: list[str], start: int | None = None, end: int | None = None) -> dict[str, TrendResult]:
    """Analyse many variables and attach FDR-adjusted q-values."""
    results = {c: analyze(df[c], c, start, end) for c in codes if c in df}
    usable = [r for r in results.values() if r.usable]
    if usable:
        q = benjamini_hochberg(np.array([r.p for r in usable]))
        for r, qi in zip(usable, q):
            r.q = float(qi)
    return results


def years_to_significance(res: TrendResult, alpha: float = 0.05, horizon: int = 60) -> int | None:
    """Extra years of record at which today's trend and noise would reach significance.

    OLS t grows like n^1.5 for a fixed slope and noise level; returns 0 if already significant
    and None if it would take more than ``horizon`` extra years (or the slope is ~zero).
    """
    if not res.usable:
        return None
    if res.p < alpha:
        return 0
    n0 = len(res.years)
    se = abs(res.ols_high - res.ols_low) / (2 * stats.t.ppf(0.975, n0 - 2))
    if se <= 0 or abs(res.ols_slope) / se < 0.25:
        return None
    t0 = abs(res.ols_slope) / se
    for extra in range(1, horizon + 1):
        n = n0 + extra
        if t0 * (n / n0) ** 1.5 >= stats.t.ppf(1 - alpha / 2, n - 2):
            return extra
    return None


# --------------------------------------------------------------------------- seasonal & relationships
def seasonal_fingerprint(series: pd.Series, start: int | None = None, end: int | None = None) -> pd.DataFrame:
    """Sen slope (per decade) and Mann-Kendall p for each calendar month separately."""
    s = series.dropna()
    if start is not None:
        s = s[s.index.year >= start]
    if end is not None:
        s = s[s.index.year <= end]
    rows = []
    for m in range(1, 13):
        sm = s[s.index.month == m]
        if len(sm) < MIN_YEARS or np.std(sm.to_numpy()) < 1e-12:
            rows.append({"month": m, "per_decade": np.nan, "p": np.nan})
            continue
        t = sm.index.year.to_numpy(dtype=float)
        x = sm.to_numpy(dtype=float)
        mk = mann_kendall(x)
        slope, _, _ = sen_slope(t, x, mk["var"])
        rows.append({"month": m, "per_decade": slope * 10, "p": mk["p"]})
    return pd.DataFrame(rows)


def detrended_anomaly_correlations(df: pd.DataFrame, codes: list[str],
                                   start: int | None = None, end: int | None = None) -> pd.DataFrame:
    """Spearman correlation of month-to-month wiggles (seasons and long-term trends removed)."""
    cols = {}
    for c in codes:
        if c not in df:
            continue
        s = df[c].dropna()
        if start is not None:
            s = s[s.index.year >= start]
        if end is not None:
            s = s[s.index.year <= end]
        if len(s) < 60 or s.std() < 1e-12:
            continue
        a = monthly_anomalies(s)
        t = np.arange(len(a), dtype=float)
        coef = np.polyfit(t, a.to_numpy(), 1)
        cols[c] = a - np.polyval(coef, t)
    return pd.DataFrame(cols).corr(method="spearman")
