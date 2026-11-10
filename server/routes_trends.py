"""Trend Detective endpoints: scan, series, guided answers, regional comparison, links, report, events."""

from __future__ import annotations

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from terrapulse import narrative as N, questions as Q, trends as T
from terrapulse.climate import PLACES, Place
from terrapulse.variables import VARIABLES

from . import state
from .serialize import answer_dict, nums, num, place_dict, scan_summary, trend_dict

router = APIRouter(prefix="/api/trends", tags=["trends"])

PlaceDep = Depends(state.place_param)
WindowDep = Depends(state.window_param)


def _variable(code: str):
    """Look up a variable or answer 404."""
    if code not in VARIABLES:
        raise HTTPException(404, f"Unknown variable '{code}'")
    return VARIABLES[code]


@router.get("/scan")
def scan(place: Place = PlaceDep, win: tuple[int, int] = WindowDep) -> dict:
    """Test all 20 variables at a place: the 'suspect board'."""
    start, end = win
    results = state.scan(place.lat, place.lon, start, end)
    return {"place": place_dict(place), "window": {"start": start, "end": end},
            "summary": scan_summary(results), "results": [trend_dict(r) for r in results.values()]}


@router.get("/series")
def series(code: str, place: Place = PlaceDep, win: tuple[int, int] = WindowDep) -> dict:
    """Everything needed to draw and explain one variable's evidence."""
    v = _variable(code)
    start, end = win
    res = state.scan(place.lat, place.lon, start, end)[code]
    if not res.usable:
        return {"usable": False, "reason": res.reason, "trend": trend_dict(res)}
    df = state.record(place.lat, place.lon)
    s = df[code].dropna()
    s = s[(s.index.year >= start) & (s.index.year <= end)]
    t = s.index.year.to_numpy() + (s.index.month.to_numpy() - 0.5) / 12
    anomalies = T.monthly_anomalies(s)
    trend = res.line_at(t)
    lo, hi = res.line_at(t, res.ci_low), res.line_at(t, res.ci_high)
    yrs = res.years.astype(float) + 0.5
    a_lo, a_hi = res.line_at(yrs, res.ci_low), res.line_at(yrs, res.ci_high)
    seasonal = T.seasonal_fingerprint(df[code], start, end)
    verdict = N.verdict(v, res, place.name, start, end)
    return {
        "usable": True,
        "place": place_dict(place), "window": {"start": start, "end": end},
        "variable": {"code": v.code, "name": v.name, "unit": v.unit, "group": v.group, "decimals": v.decimals,
                     "definition": v.definition, "risingMeans": v.rising_means},
        "trend": trend_dict(res),
        "monthly": {
            "dates": [d.strftime("%Y-%m") for d in s.index],
            "values": nums(s.to_numpy(), 4), "anomalies": nums(anomalies.to_numpy(), 4),
            "smooth": nums(s.rolling(12, min_periods=9, center=True).mean().to_numpy(), 4),
            "smoothAnomaly": nums(anomalies.rolling(12, min_periods=9, center=True).mean().to_numpy(), 4),
            "trend": nums(trend, 4), "trendAnomaly": nums(trend - res.mean, 4),
            "wedgeLow": nums(np.minimum(lo, hi), 4), "wedgeHigh": nums(np.maximum(lo, hi), 4),
            "wedgeLowAnomaly": nums(np.minimum(lo, hi) - res.mean, 4),
            "wedgeHighAnomaly": nums(np.maximum(lo, hi) - res.mean, 4),
        },
        "annual": {"years": [int(y) for y in res.years], "values": nums(res.annual, 4),
                   "trend": nums(res.line_at(yrs), 4), "wedgeLow": nums(np.minimum(a_lo, a_hi), 4),
                   "wedgeHigh": nums(np.maximum(a_lo, a_hi), 4)},
        "seasonal": [{"month": int(r.month), "perDecade": num(r.per_decade, 5), "p": num(r.p, 5)}
                     for r in seasonal.itertuples()],
        "verdict": verdict,
        "jumpWarning": N.jump_warning(v, res),
        "yearsToSignificance": T.years_to_significance(res),
        "probabilityText": N.plain_p(res.p),
    }


@router.get("/answer")
def answer(question: str, place: Place = PlaceDep, win: tuple[int, int] = WindowDep) -> dict:
    """The detective's answer to a guided question ('surprise' picks the clearest signals)."""
    start, end = win
    results = state.scan(place.lat, place.lon, start, end)
    if question == "surprise":
        codes = Q.surprise_me(results)
        lines = [f"{VARIABLES[c].name}: {N.rate_text(VARIABLES[c], results[c])}" for c in codes]
        return {"id": "surprise", "text": "Surprise me", "why": "The clearest signals at this place.",
                "outcome": "up", "headline": "Three clues worth a look", "body": " · ".join(lines),
                "tone": "sig", "codes": codes}
    q = Q.QUESTIONS_BY_ID.get(question)
    if q is None:
        raise HTTPException(404, f"Unknown question '{question}'")
    return answer_dict(q, Q.answer(q, results))


def _finding(df: pd.DataFrame, code: str) -> dict:
    """Headline about the signs of the significant places: opposite stories, one-way, or nothing clear."""
    v = VARIABLES[code]
    rising = df[df["significant"] & (df["per_decade"] > 0)].sort_values("per_decade")
    falling = df[df["significant"] & (df["per_decade"] < 0)].sort_values("per_decade")
    out = {"rising": len(rising), "falling": len(falling), "none": len(df) - len(rising) - len(falling)}
    d = v.decimals
    if len(rising) and len(falling):
        hi, lo = rising.iloc[-1], falling.iloc[0]
        out.update(kind="opposite", headline="Same variable, opposite stories",
                   body=(f"{v.name} is rising in {hi['name']} ({N.signed(hi['per_decade'], d)} {v.unit}/decade) but "
                         f"falling in {lo['name']} ({N.signed(lo['per_decade'], d)}). A single global average would hide both."))
    elif len(rising) or len(falling):
        way = "rising" if len(rising) else "falling"
        out.update(kind="one-way", headline=f"Every significant place is {way}",
                   body=f"No place shows a significant move in the opposite direction for {v.name.lower()} in this window.")
    else:
        out.update(kind="none", headline="No place shows a clear trend",
                   body="Natural variation cannot be ruled out anywhere in this window.")
    return out


@router.get("/regional")
def regional(code: str, place: Place = PlaceDep, win: tuple[int, int] = WindowDep) -> dict:
    """The same variable at every built-in place, so opposite trends show up side by side."""
    _variable(code)
    start, end = win
    extra = None if place.name in PLACES else (place.name, place.lat, place.lon, place.biome, place.blurb)
    df = state.regional(code, start, end, extra)
    if df.empty:
        return {"code": code, "rows": [], "finding": {"kind": "none", "headline": "No testable record", "body": ""}}
    rows = [{"name": r.name, "lat": r.lat, "lon": r.lon, "biome": r.biome, "perDecade": num(r.per_decade, 5),
             "p": num(r.p, 5), "q": num(r.q, 5), "significant": bool(r.significant), "jump": bool(r.jump)}
            for r in df.itertuples()]
    return {"code": code, "rows": rows, "finding": _finding(df, code)}


@router.get("/correlations")
def correlations(place: Place = PlaceDep, win: tuple[int, int] = WindowDep) -> dict:
    """How variables move together, the explained links, and the multi-variable story."""
    start, end = win
    corr = state.corr(place.lat, place.lon, start, end)
    results = state.scan(place.lat, place.lon, start, end)
    links = N.top_connections(corr, k=7)
    return {
        "codes": list(corr.columns), "names": [VARIABLES[c].name for c in corr.columns],
        "matrix": [nums(row, 3) for row in corr.to_numpy()],
        "links": [{**lk, "aName": VARIABLES[lk["a"]].name, "bName": VARIABLES[lk["b"]].name,
                   "rho": num(lk["rho"], 3)} for lk in links],
        "story": N.earth_story(results),
    }


@router.get("/report")
def report(place: Place = PlaceDep, win: tuple[int, int] = WindowDep) -> Response:
    """A shareable Markdown case file for one place."""
    start, end = win
    text = N.case_report_md(place.name, place.lat, place.lon, start, end, state.scan(place.lat, place.lon, start, end))
    name = place.name.split(",")[0].replace(" ", "_").lower()
    return Response(text, media_type="text/markdown",
                    headers={"Content-Disposition": f'attachment; filename="case_file_{name}.md"'})


@router.get("/events")
def events() -> dict:
    """Currently active natural events (wildfires, storms, sea ice) from an open feed."""
    try:
        df = state.events()
    except Exception as exc:
        raise HTTPException(503, f"The live event feed is not reachable: {exc}") from exc
    return {"events": df.to_dict(orient="records")}
