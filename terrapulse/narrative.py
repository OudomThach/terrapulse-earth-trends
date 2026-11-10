"""Turns statistics into plain-language explanations. Pure functions, no UI."""

from __future__ import annotations

import numpy as np

from .trends import TrendResult, evidence_label, years_to_significance
from .variables import VARIABLES, Variable

MINUS = "−"


def signed(v: float, decimals: int = 2) -> str:
    """+1.23 / −0.40 with a real minus sign and thousands separators."""
    if v is None or not np.isfinite(v):
        return "n/a"
    s = f"{v:+,.{decimals}f}"
    return s.replace("-", MINUS)


def plain_p(p: float) -> str:
    """Chance of a pattern this strong arising by luck if nothing were changing."""
    if p < 0.001:
        return "less than 1 time in 1,000"
    if p < 0.01:
        return f"about {max(1, round(p * 1000))} times in 1,000"
    if p < 0.995:
        return f"about {round(p * 100)} times in 100"
    return "almost every time"


def strength_dots(p: float) -> str:
    """Evidence meter that does not rely on colour: ●●● / ●●○ / ●○○ / ○○○."""
    return "●●●" if p < 0.01 else "●●○" if p < 0.05 else "●○○" if p < 0.10 else "○○○"


def rate_text(v: Variable, res: TrendResult) -> str:
    """The rate of change as text, for example '+0.73 degC per decade'."""
    return f"{signed(res.per_decade, v.decimals)} {v.unit} per decade"


def verdict(v: Variable, res: TrendResult, place: str, start: int, end: int) -> dict:
    """Headline + explanation for one variable. ``tone`` is strong / sig / weak / none."""
    if not res.usable:
        return {"tone": "none", "headline": f"{v.name}: nothing to test", "body": res.reason, "label": "Not testable"}
    label = evidence_label(res.p)
    tone = {"Strong evidence": "strong", "Significant": "sig", "Weak hint": "weak"}.get(label, "none")
    d = v.decimals
    word = "rising" if res.slope > 0 else "falling"
    if tone in ("strong", "sig"):
        headline = f"{v.name} is {word}: {rate_text(v, res)}"
    elif tone == "weak":
        headline = f"{v.name} leans {word}, but the evidence is weak"
    else:
        headline = f"No clear trend in {v.name.lower()}"
    pct = res.pct_change
    pct_txt = f" ({signed(pct, 0)}% of the average)" if np.isfinite(pct) and abs(pct) < 1e4 else ""
    body = (f"Between {start} and {end} in {place}, the best estimate of change is "
            f"**{rate_text(v, res)}**, with a 95% confidence range of {signed(res.ci_low * 10, d)} to "
            f"{signed(res.ci_high * 10, d)}. Over {res.span_years:.0f} years that adds up to about "
            f"**{signed(res.total_change, d)} {v.unit}**{pct_txt}. ")
    if tone in ("strong", "sig"):
        body += (f"If nothing were really changing, a pattern this strong would appear by luck "
                 f"{plain_p(res.p)}, so we call it statistically significant.")
    else:
        body += ("The range of plausible rates includes zero, so we cannot rule out ordinary natural "
                 "variation. ")
        extra = years_to_significance(res)
        if extra:
            body += f"If today's pace and noise continued, roughly **{extra} more years** of data would make it significant."
        elif extra is None:
            body += "At this pace even decades more data would not make it clear, so the rate may truly be near zero."
    return {"tone": tone, "headline": headline, "body": body, "label": label}


def jump_warning(v: Variable, res: TrendResult) -> str | None:
    """A caution paragraph if the record looks like one sudden step, otherwise None."""
    if not res.suspicious_jump:
        return None
    d = v.decimals
    return (f"**Possible data jump in {res.jump_year}.** The record sits near {res.jump_before:,.{d}f} {v.unit} "
            f"before and {res.jump_after:,.{d}f} {v.unit} after, and one sudden step fits the data much better "
            f"than a steady slope. Real climate usually changes gradually; an abrupt step often comes from a "
            f"change in instruments or data processing. Treat the trend below with caution, and try re-testing "
            f"from {res.jump_year} onward.")


# --------------------------------------------------------------------------- relationships
# (code_a, code_b) -> (expected sign of the month-to-month link, plain explanation)
LINK_HINTS: dict[frozenset, tuple[int, str]] = {
    frozenset({"T2M", "QV2M"}): (+1, "Warmer air can hold more water vapour (roughly 7% more for each °C)."),
    frozenset({"T2M", "RH2M"}): (-1, "When air warms, the same moisture fills less of its capacity, so relative humidity falls."),
    frozenset({"PRECTOTCORR", "GWETROOT"}): (+1, "Rain refills the soil."),
    frozenset({"PRECTOTCORR", "GWETTOP"}): (+1, "Rain wets the soil surface first."),
    frozenset({"CLOUD_AMT", "ALLSKY_SFC_SW_DWN"}): (-1, "Clouds block sunlight."),
    frozenset({"AOD_55", "ALLSKY_SFC_SW_DWN"}): (-1, "Haze particles scatter and absorb sunlight."),
    frozenset({"QV2M", "ALLSKY_SFC_LW_DWN"}): (+1, "Water vapour is a greenhouse gas: it re-radiates heat back down."),
    frozenset({"CLOUD_AMT", "ALLSKY_SFC_LW_DWN"}): (+1, "Clouds act like a blanket, sending heat back to the ground."),
    frozenset({"RH2M", "CLOUD_AMT"}): (+1, "Moist air condenses into cloud."),
    frozenset({"PRECTOTCORR", "CLOUD_AMT"}): (+1, "Rain needs clouds."),
    frozenset({"T2M", "ALLSKY_SFC_SW_DWN"}): (+1, "Sunny spells heat the ground and the air above it."),
    frozenset({"EVLAND", "ALLSKY_SFC_SW_DWN"}): (+1, "Sunlight supplies the energy that evaporates water."),
    frozenset({"T2M", "FROST_DAYS"}): (-1, "Warmer months have fewer freezing days."),
    frozenset({"T2M", "SNODP"}): (-1, "Warmth melts snow."),
}

# Variables that measure nearly the same thing; pairing them would be a trivial 'discovery'.
FAMILIES = [
    {"T2M", "T2M_MAX", "T2M_MIN", "TS", "T10M"},
    {"GWETROOT", "GWETTOP"},
    {"QV2M", "TQV"},
]


def _same_family(a: str, b: str) -> bool:
    return any(a in f and b in f for f in FAMILIES)


def top_connections(corr, k: int = 8, min_abs: float = 0.35) -> list[dict]:
    """Strongest non-trivial month-to-month relationships, each with an explanation if known."""
    out, seen = [], set()
    cols = list(corr.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            rho = corr.loc[a, b]
            if not np.isfinite(rho) or abs(rho) < min_abs or _same_family(a, b):
                continue
            key = frozenset({a, b})
            if key in seen:
                continue
            seen.add(key)
            hint = LINK_HINTS.get(key)
            if hint is None:
                note, matches = None, None
            else:
                matches = bool(np.sign(rho) == hint[0])
                note = hint[1] if matches else f"Unexpected here: normally {hint[1][0].lower() + hint[1][1:]}"
            out.append({"a": a, "b": b, "rho": float(rho), "note": note, "matches": matches})
    out.sort(key=lambda r: (r["note"] is None, -abs(r["rho"])))   # explainable links first
    return out[:k]


def earth_story(results: dict[str, TrendResult]) -> list[dict]:
    """Rule-based multi-variable reading of the significant trends ('consistent with', never 'caused by')."""
    def sig(code):
        """The result for ``code`` if it is a clear (significant, non-jump) trend, else None."""
        r = results.get(code)
        return r if (r and r.usable and r.q < 0.05 and not r.suspicious_jump) else None

    def line(code):
        """Short 'name +rate unit/decade' phrase for one variable."""
        v, r = VARIABLES[code], results[code]
        return f"{v.name.lower()} {signed(r.per_decade, v.decimals)} {v.unit}/decade"

    story = []
    warm = [c for c in ("T2M", "TS") if sig(c) and results[c].slope > 0]
    cool = [c for c in ("T2M", "TS", "T2M_MAX") if sig(c) and results[c].slope < 0]
    if warm:
        story.append({"title": "The place is warming",
                      "text": f"Measured warming ({line(warm[0])}). Warmer surfaces and air are the starting point for most of the other changes below.",
                      "codes": warm})
    if cool:
        story.append({"title": "A surprise: cooling",
                      "text": f"Temperature here is falling ({line(cool[0])}) even though most of the planet is warming. Trends can differ by region, so look for a local process such as haze, irrigation or changing cloud.",
                      "codes": cool})
    mn, mx = sig("T2M_MIN"), sig("T2M_MAX")
    if mn and mx and mn.slope > 0 and mx.slope > 0 and mn.slope > 1.5 * mx.slope:
        story.append({"title": "Nights are warming faster than days",
                      "text": f"{line('T2M_MIN')} versus {line('T2M_MAX')}. Heat that is trapped near the surface (by water vapour, cloud or greenhouse gases) shows up most at night, when there is no sunshine to compare it with.",
                      "codes": ["T2M_MIN", "T2M_MAX"]})
    wet = [c for c in ("QV2M", "TQV") if sig(c) and results[c].slope > 0]
    if warm and wet:
        story.append({"title": "More water vapour in warmer air",
                      "text": f"Air holds roughly 7% more vapour per °C of warming, and the record agrees ({line(wet[0])}). Vapour is itself a greenhouse gas, so this can amplify the warming.",
                      "codes": wet})
    lw = sig("ALLSKY_SFC_LW_DWN")
    if lw and lw.slope > 0:
        story.append({"title": "The sky is sending more heat down",
                      "text": f"{line('ALLSKY_SFC_LW_DWN')}: a direct sign of a more heat-trapping atmosphere above the place.",
                      "codes": ["ALLSKY_SFC_LW_DWN"]})
    sw, aod, cld = sig("ALLSKY_SFC_SW_DWN"), sig("AOD_55"), sig("CLOUD_AMT")
    if sw and sw.slope < 0 and aod and aod.slope > 0:
        story.append({"title": "Dimming: more haze, less sun",
                      "text": f"{line('ALLSKY_SFC_SW_DWN')} while {line('AOD_55')}. Particle pollution is consistent with sunlight being blocked before it reaches the ground.",
                      "codes": ["ALLSKY_SFC_SW_DWN", "AOD_55"]})
    elif sw and sw.slope < 0 and cld and cld.slope > 0:
        story.append({"title": "Cloudier and dimmer",
                      "text": f"{line('ALLSKY_SFC_SW_DWN')} alongside {line('CLOUD_AMT')}: more cloud is consistent with less sunshine reaching the surface.",
                      "codes": ["ALLSKY_SFC_SW_DWN", "CLOUD_AMT"]})
    elif sw and sw.slope > 0 and cld and cld.slope < 0:
        story.append({"title": "Clearer skies, more sun",
                      "text": f"{line('ALLSKY_SFC_SW_DWN')} alongside {line('CLOUD_AMT')}: fewer clouds are consistent with more sunshine reaching the surface.",
                      "codes": ["ALLSKY_SFC_SW_DWN", "CLOUD_AMT"]})
    pr, sr = sig("PRECTOTCORR"), sig("GWETROOT")
    if pr and sr and np.sign(pr.slope) == np.sign(sr.slope):
        wetter = pr.slope > 0
        story.append({"title": f"Rainfall and soil are {'wetter' if wetter else 'drier'} together",
                      "text": f"{line('PRECTOTCORR')} and {line('GWETROOT')}: the water cycle is shifting in one direction, and soil moisture follows the rain.",
                      "codes": ["PRECTOTCORR", "GWETROOT"]})
    elif sr and sr.slope < 0 and warm:
        story.append({"title": "Warmer and drier soil",
                      "text": f"{line('GWETROOT')} while temperatures rise: heat speeds up evaporation, which dries soil even if rainfall is unchanged.",
                      "codes": ["GWETROOT"] + warm})
    cold = [c for c in ("FROST_DAYS", "SNODP") if sig(c) and results[c].slope < 0]
    if cold and warm:
        story.append({"title": "Less frost and snow",
                      "text": f"{line(cold[0])}: the cold season is shrinking as the place warms.",
                      "codes": cold})
    for item in story:   # sentences that begin with a variable name start in lower case
        item["text"] = item["text"][0].upper() + item["text"][1:]
    return story


def case_report_md(place: str, lat: float, lon: float, start: int, end: int, results: dict[str, TrendResult]) -> str:
    """A shareable Markdown 'case file' for the scan of one place."""
    usable = [r for r in results.values() if r.usable]
    usable.sort(key=lambda r: (r.q, -abs(r.z)))
    lines = [f"# Trend Detective case file: {place}", "",
             f"Location {lat:.2f}, {lon:.2f}. Period {start} to {end}. {len(usable)} variables tested.", "",
             "Method: annual means, Mann-Kendall test (autocorrelation-adjusted), Sen's slope with 95% CI, "
             "Benjamini-Hochberg false-discovery correction across all variables.", "",
             "| Variable | Change per decade | 95% CI | p | q (adjusted) | Verdict | Notes |", "|---|---|---|---|---|---|---|"]
    for r in usable:
        v = VARIABLES[r.code]
        note = f"possible data jump in {r.jump_year}" if r.suspicious_jump else ""
        lines.append(f"| {v.name} | {signed(r.per_decade, v.decimals)} {v.unit} | "
                     f"{signed(r.ci_low * 10, v.decimals)} to {signed(r.ci_high * 10, v.decimals)} | "
                     f"{r.p:.4f} | {r.q:.4f} | {evidence_label(r.q)} | {note} |")
    lines += ["", "A trend shows what is changing, not why. Reanalysis data blend observations with a weather model; "
              "abrupt jumps can reflect changes in the observing system.", ""]
    return "\n".join(lines)
