"""Long monthly Earth-system records for any place on the planet, cached on disk,
plus a live feed of currently active natural events."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd
import requests

from .config import CACHE_DIR
from .variables import CODES

POWER_MONTHLY_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
EVENTS_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"
FILL_VALUE = -999.0
FIRST_YEAR, LAST_YEAR = 1990, 2025


class ClimateDataError(RuntimeError):
    """The record for a place could not be loaded (offline and not cached)."""


@dataclass(frozen=True)
class Place:
    """A named location with its biome and a one-line description."""

    name: str
    lat: float
    lon: float
    biome: str
    blurb: str


PLACES: dict[str, Place] = {p.name: p for p in [
    Place("Svalbard, Arctic", 78.2, 15.6, "Polar", "Sea ice and tundra only 1,300 km from the North Pole."),
    Place("Greenland ice sheet", 72.5, -38.5, "Polar", "A two-mile-thick ice sheet holding 7 m of potential sea level."),
    Place("Siberian taiga", 62.0, 129.7, "Boreal forest", "The coldest large forest on Earth, with permafrost below."),
    Place("Tibetan Plateau", 31.5, 91.0, "Mountain", "The 'third pole': a high, dry roof of the world."),
    Place("Sahara Desert", 25.0, 10.0, "Desert", "The world's largest hot desert."),
    Place("Sahel, Niger", 14.0, 2.0, "Semi-arid", "Dry belt south of the Sahara, tied to the West African monsoon."),
    Place("Amazon rainforest", -3.5, -62.0, "Rainforest", "Half of the world's tropical forest, making much of its own rain."),
    Place("Congo basin", 0.5, 23.5, "Rainforest", "Africa's equatorial rainforest."),
    Place("Borneo rainforest", 0.5, 114.0, "Rainforest", "Equatorial island forest on the edge of the Pacific warm pool."),
    Place("Great Plains, Kansas", 38.9, -99.3, "Grassland", "America's farm belt, sensitive to drought."),
    Place("California Central Valley", 36.75, -119.8, "Farmland", "An irrigated valley that grows much of the US produce."),
    Place("Seattle region", 47.6, -122.3, "Temperate coast", "Wet, mild Pacific Northwest coast."),
    Place("Mediterranean Spain", 39.5, -3.5, "Mediterranean", "Dry-summer climate and a climate-change hotspot."),
    Place("Delhi & Gangetic plain", 28.6, 77.2, "Megacity", "A dense, hazy urban plain of 30+ million people."),
    Place("Tonle Sap, Cambodia", 12.8, 104.0, "Monsoon wetland", "A lake whose flow reverses with the monsoon."),
    Place("Australian outback", -25.5, 134.0, "Desert", "Dry interior of Australia."),
    Place("Johannesburg region", -26.2, 28.0, "Highveld", "High, dry plateau in southern Africa."),
    Place("Mexico City basin", 19.4, -99.1, "Megacity", "A high-altitude megacity in a closed valley."),
    Place("Antarctic Peninsula", -65.0, -64.0, "Polar", "The fastest-warming corner of Antarctica."),
]}

CUSTOM = "Custom location..."


def cache_file(lat: float, lon: float):
    """Path of the on-disk cache for one place's monthly record."""
    tag = f"{lat:.2f}_{lon:.2f}".replace("-", "m")
    return CACHE_DIR / f"monthly_{tag}.csv"


def parse_monthly(payload: dict) -> pd.DataFrame:
    """Turn a monthly API response into a DataFrame indexed by month start."""
    table = payload["properties"]["parameter"]
    cols = {}
    for code, series in table.items():
        rows = {k: v for k, v in series.items() if k[4:6] != "13"}  # drop 'annual mean' rows
        idx = pd.to_datetime([k + "01" for k in rows], format="%Y%m%d")
        cols[code] = pd.Series(list(rows.values()), index=idx, dtype=float)
    df = pd.DataFrame(cols).sort_index().replace(FILL_VALUE, np.nan)
    df.index.name = "month"
    return _complete(df)


def _complete(df: pd.DataFrame) -> pd.DataFrame:
    """Always expose every catalogued variable; ones with no data at a place are simply all-NaN."""
    out = df.reindex(columns=CODES)
    out.index.name = "month"
    return out


def _read_cache(path) -> pd.DataFrame:
    return _complete(pd.read_csv(path, index_col=0, parse_dates=True))


def load_monthly(lat: float, lon: float, refresh: bool = False, retries: int = 3) -> pd.DataFrame:
    """Monthly record for (lat, lon), 1990-2025. Uses the disk cache when present."""
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("latitude must be in [-90, 90] and longitude in [-180, 180]")
    path = cache_file(lat, lon)
    if path.exists() and not refresh:
        return _read_cache(path)
    params = {"parameters": ",".join(CODES), "community": "AG", "longitude": lon, "latitude": lat,
              "start": FIRST_YEAR, "end": LAST_YEAR, "format": "JSON"}
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(POWER_MONTHLY_URL, params=params, timeout=90)
            resp.raise_for_status()
            df = parse_monthly(resp.json())
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            df.to_csv(path)
            return df
        except (requests.RequestException, KeyError, ValueError) as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    if path.exists():
        return _read_cache(path)
    raise ClimateDataError(f"Could not load the record for {lat:.2f}, {lon:.2f}: {last_err}")


def prefetch_all(workers: int = 4) -> dict[str, str]:
    """Download and cache every preset place (used before a demo, and by the Where tab)."""
    def one(place: Place):
        """Download one place, returning (name, 'ok' or the error)."""
        try:
            load_monthly(place.lat, place.lon)
            return place.name, "ok"
        except Exception as exc:  # report, don't crash the batch
            return place.name, f"failed: {exc}"
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(one, PLACES.values()))


def fetch_events(days: int = 30, limit: int = 400) -> pd.DataFrame:
    """Currently open natural events (wildfires, storms, volcanoes, ...) as point locations."""
    resp = requests.get(EVENTS_URL, params={"status": "open", "days": days, "limit": limit}, timeout=30)
    resp.raise_for_status()
    rows = []
    for ev in resp.json().get("events", []):
        geoms = [g for g in ev.get("geometry", []) if g.get("type") == "Point"]
        if not geoms:
            continue
        g = geoms[-1]
        lon, lat = g["coordinates"][:2]
        rows.append({"title": ev["title"], "category": ev["categories"][0]["title"],
                     "date": g.get("date", "")[:10], "lat": lat, "lon": lon})
    return pd.DataFrame(rows, columns=["title", "category", "date", "lat", "lon"])
