"""Turn analysis objects into JSON-safe dictionaries (NaN and infinity become null)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from terrapulse import narrative as N, trends as T
from terrapulse.climate import Place
from terrapulse.questions import Answer, Question
from terrapulse.trends import TrendResult
from terrapulse.variables import VARIABLES, Variable


def num(x: Any, digits: int | None = None) -> float | None:
    """A float that JSON can carry: None for missing, NaN or infinite values."""
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return round(f, digits) if digits is not None else f


def nums(values, digits: int = 4) -> list[float | None]:
    """A list of JSON-safe numbers from any array-like."""
    return [num(v, digits) for v in np.asarray(values, dtype=float).tolist()]


def place_dict(p: Place) -> dict:
    """A place as the front end needs it."""
    return {"name": p.name, "lat": p.lat, "lon": p.lon, "biome": p.biome, "blurb": p.blurb}


def variable_dict(v: Variable) -> dict:
    """Catalog entry for one variable."""
    return {"code": v.code, "name": v.name, "unit": v.unit, "group": v.group, "definition": v.definition,
            "risingMeans": v.rising_means, "decimals": v.decimals, "since": v.since}


def question_dict(q: Question) -> dict:
    """Catalog entry for one guided question."""
    return {"id": q.id, "text": q.text, "why": q.why, "clues": list(q.clues)}


def answer_dict(q: Question, a: Answer) -> dict:
    """The detective's answer to a guided question."""
    return {"id": q.id, "text": q.text, "why": q.why, "outcome": a.outcome, "headline": a.headline,
            "body": a.body, "tone": a.tone, "codes": a.codes}


def trend_dict(res: TrendResult) -> dict:
    """Everything the interface shows about one variable's trend (rates are per decade)."""
    v = VARIABLES[res.code]
    base = {"code": res.code, "name": v.name, "unit": v.unit, "group": v.group, "decimals": v.decimals,
            "usable": res.usable, "reason": res.reason}
    if not res.usable:
        return base
    shown_p = res.q if math.isfinite(res.q) else res.p
    return {
        **base,
        "perDecade": num(res.per_decade), "ciLow": num(res.ci_low * 10), "ciHigh": num(res.ci_high * 10),
        "p": num(res.p), "q": num(res.q), "z": num(res.z), "tau": num(res.tau),
        "label": T.evidence_label(shown_p), "dots": N.strength_dots(shown_p), "direction": res.direction,
        "totalChange": num(res.total_change), "pctChange": num(res.pct_change), "spanYears": res.span_years,
        "mean": num(res.mean), "lag1": num(res.lag1), "inflation": num(res.inflation),
        "rateText": N.rate_text(v, res),
        "ols": {"perDecade": num(res.ols_slope * 10), "low": num(res.ols_low * 10), "high": num(res.ols_high * 10),
                "r2": num(res.ols_r2), "p": num(res.ols_p)},
        "jump": {"year": res.jump_year, "p": num(res.jump_p), "before": num(res.jump_before),
                 "after": num(res.jump_after), "fitRatio": num(res.jump_fit_ratio),
                 "suspicious": res.suspicious_jump},
        "annual": {"years": [int(y) for y in res.years], "values": nums(res.annual)},
    }


def scan_summary(results: dict[str, TrendResult]) -> dict:
    """Headline numbers for a whole scan."""
    usable = [r for r in results.values() if r.usable]
    sig = [r for r in usable if r.q < 0.05]
    clean = [r for r in sig if not r.suspicious_jump]
    best = min(clean, key=lambda r: (r.q, -abs(r.z)), default=None)
    strongest = None
    if best is not None:
        strongest = {"code": best.code, "name": VARIABLES[best.code].name, "rateText": N.rate_text(VARIABLES[best.code], best),
                     "direction": best.direction}
    return {"tested": len(usable), "available": len(results), "significant": len(sig),
            "jumps": sum(1 for r in usable if r.suspicious_jump), "strongest": strongest}
