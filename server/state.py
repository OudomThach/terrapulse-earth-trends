"""Shared, cached building blocks for the routes: place resolution, windows and memoised analysis."""

from __future__ import annotations

import time
from functools import lru_cache

import pandas as pd
from fastapi import HTTPException, Query

from terrapulse import trends as T
from terrapulse.climate import FIRST_YEAR, LAST_YEAR, PLACES, Place, fetch_events, load_monthly
from terrapulse.db import Database
from terrapulse.variables import CODES


# ----------------------------------------------------------------------------- request parameters
def place_param(place: str | None = Query(None, description="Name of a built-in place"),
                lat: float | None = Query(None, ge=-90, le=90), lon: float | None = Query(None, ge=-180, le=180)) -> Place:
    """Resolve ?place=NAME or ?lat=&lon= into a Place (a custom point gets a generic description)."""
    if place:
        if place not in PLACES:
            raise HTTPException(404, f"Unknown place '{place}'")
        return PLACES[place]
    if lat is None or lon is None:
        raise HTTPException(422, "Give either ?place=NAME or both ?lat= and ?lon=")
    return Place(f"Custom ({lat:.2f}, {lon:.2f})", round(lat, 2), round(lon, 2), "Custom location",
                 "Your own spot. Each data cell is about 50 km wide, so this is a regional average.")


def window_param(start: int = Query(FIRST_YEAR, ge=FIRST_YEAR, le=LAST_YEAR),
                 end: int = Query(LAST_YEAR, ge=FIRST_YEAR, le=LAST_YEAR)) -> tuple[int, int]:
    """Validate the year window: at least ten years, in order."""
    if end - start < 9:
        raise HTTPException(422, "Pick at least 10 years: shorter windows are mostly natural variation.")
    return start, end


# ----------------------------------------------------------------------------- memoised analysis
@lru_cache(maxsize=256)
def record(lat: float, lon: float) -> pd.DataFrame:
    """Monthly record for a place (also cached on disk). Treat the result as read-only."""
    return load_monthly(lat, lon)


@lru_cache(maxsize=512)
def scan(lat: float, lon: float, start: int, end: int) -> dict:
    """Trend test of every variable at a place, with false-discovery-corrected q-values."""
    return T.scan(record(lat, lon), CODES, start, end)


@lru_cache(maxsize=128)
def corr(lat: float, lon: float, start: int, end: int) -> pd.DataFrame:
    """Link strengths between all variables at a place."""
    return T.detrended_anomaly_correlations(record(lat, lon), CODES, start, end)


@lru_cache(maxsize=256)
def regional(code: str, start: int, end: int, extra: tuple | None) -> pd.DataFrame:
    """One variable's trend at every built-in place (and ``extra``, a custom place as a tuple)."""
    places = list(PLACES.values()) + ([Place(*extra)] if extra else [])
    rows = []
    for p in places:
        r = T.analyze(record(p.lat, p.lon)[code], code, start, end)
        if r.usable:
            rows.append(dict(name=p.name, lat=p.lat, lon=p.lon, biome=p.biome, per_decade=r.per_decade, p=r.p,
                             jump=bool(r.suspicious_jump)))
    df = pd.DataFrame(rows)
    if len(df):
        df["q"] = T.benjamini_hochberg(df["p"].to_numpy())
        df["significant"] = df["q"] < 0.05
    return df


_EVENTS: tuple[float, pd.DataFrame] | None = None


def events(max_age_s: float = 3600.0) -> pd.DataFrame:
    """Currently open natural events, refreshed at most once an hour."""
    global _EVENTS
    if _EVENTS is None or time.time() - _EVENTS[0] > max_age_s:
        _EVENTS = (time.time(), fetch_events())
    return _EVENTS[1]


# ----------------------------------------------------------------------------- storage
_DB: Database | None = None


def db() -> Database:
    """The shared SQLite store (created on first use)."""
    global _DB
    if _DB is None:
        _DB = Database()
    return _DB
