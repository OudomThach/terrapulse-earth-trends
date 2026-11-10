"""Data layer: satellite reanalysis fetcher (with disk cache) and real elevation tiles (with a synthetic fallback)."""

from __future__ import annotations

import datetime as dt
import io
import json
import math

import numpy as np
import pandas as pd
import requests
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates

from .config import CACHE_DIR, FEATURES, Region

POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
FILL_VALUE = -999.0
TERRAIN_TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"   # open elevation tiles, no key needed
TERRAIN_ZOOM = 13          # about 19 m per pixel at the equator
REAL_TERRAIN = "real elevation (open terrain tiles)"
SYNTHETIC_TERRAIN = "synthetic placeholder terrain"


class PowerDataFetcher:
    """Downloads daily satellite reanalysis data for one point and caches it as CSV.

    If the network is unavailable and nothing is cached, ``synthetic_series`` is used
    so the app still runs. ``self.source`` always says which one you got.
    """

    def __init__(self, region: Region, start: str = "2015-01-01", timeout: int = 60):
        """Remember the region, first year to download and request timeout."""
        self.region = region
        self.start = start
        self.timeout = timeout
        self.source = "unknown"

    @property
    def cache_file(self):
        """Path of this region's cached daily CSV."""
        safe = f"{self.region.lat:.2f}_{self.region.lon:.2f}".replace("-", "m")
        return CACHE_DIR / f"power_{safe}.csv"

    def load(self, refresh: bool = False) -> pd.DataFrame:
        """Daily record from the cache, the network, or a flagged synthetic fallback (in that order)."""
        if self.cache_file.exists() and not refresh:
            self.source = "satellite reanalysis (cached)"
            return pd.read_csv(self.cache_file, index_col=0, parse_dates=True)
        try:
            df = self._download()
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            df.to_csv(self.cache_file)
            self.source = "satellite reanalysis (live download)"
            return df
        except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError):
            if self.cache_file.exists():
                self.source = "satellite reanalysis (cached, refresh failed)"
                return pd.read_csv(self.cache_file, index_col=0, parse_dates=True)
            self.source = "SYNTHETIC fallback (offline)"
            return synthetic_series(self.region)

    def _download(self) -> pd.DataFrame:
        # The newest few days are not published yet, so stop a week ago.
        end = dt.date.today() - dt.timedelta(days=7)
        params = {
            "parameters": ",".join(FEATURES),
            "community": "AG",
            "longitude": self.region.lon,
            "latitude": self.region.lat,
            "start": self.start.replace("-", ""),
            "end": end.strftime("%Y%m%d"),
            "format": "JSON",
        }
        resp = requests.get(POWER_URL, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return parse_power_json(resp.json())


def parse_power_json(payload: dict) -> pd.DataFrame:
    """Turn a satellite reanalysis JSON response into a clean daily DataFrame."""
    table = payload["properties"]["parameter"]
    df = pd.DataFrame(table)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"
    df = df.replace(FILL_VALUE, np.nan).sort_index()
    # short gaps are interpolated; anything longer is dropped rather than invented
    df = df.interpolate(limit=3).dropna()
    return df


def synthetic_series(region: Region, days: int = 3000) -> pd.DataFrame:
    """Offline stand-in with a plausible seasonal cycle (clearly flagged by the fetcher)."""
    rng = np.random.default_rng(region.seed)
    idx = pd.date_range(end=dt.date.today() - dt.timedelta(days=7), periods=days, freq="D")
    doy = idx.dayofyear.to_numpy()
    temp = 12 + 14 * np.sin(2 * np.pi * (doy - 110) / 365.25) + rng.normal(0, 3, days)
    rain = rng.gamma(0.4, 6, days) * (rng.random(days) < 0.28)
    wet = np.empty(days)
    wet[0] = 0.5
    for i in range(1, days):
        wet[i] = np.clip(wet[i - 1] * 0.985 + 0.012 * rain[i] - 0.0006 * max(temp[i], 0), 0.05, 0.95)
    return pd.DataFrame(
        {
            "GWETROOT": wet,
            "T2M": temp,
            "PRECTOTCORR": rain,
            "RH2M": np.clip(60 - 0.8 * (temp - 12) + rng.normal(0, 8, days), 10, 100),
            "WS2M": np.clip(rng.gamma(4, 0.6, days), 0.2, None),
        },
        index=pd.DatetimeIndex(idx, name="date"),
    )


def make_terrain(region: Region, size: int = 80, cell_m: float = 30.0) -> np.ndarray:
    """Reproducible synthetic elevation tile in metres (size x size, row 0 = south).

    Only a fallback for when real elevation tiles cannot be downloaded (see ``load_terrain``). It is smooth,
    hill-like terrain whose roughness depends on the region's ``relief_m``.
    """
    rng = np.random.default_rng(region.seed)
    noise = rng.normal(size=(size, size))
    broad = gaussian_filter(noise, sigma=size / 7, mode="reflect")
    fine = gaussian_filter(noise, sigma=size / 25, mode="reflect")
    z = broad / np.abs(broad).max() + 0.25 * fine / np.abs(fine).max()
    z = (z - z.min()) / (z.max() - z.min())
    return 500.0 + z * region.relief_m


def _tile_pixels(lat: float, lon: float, zoom: int) -> tuple[float, float, float]:
    """Web-mercator pixel position of a point at ``zoom``, plus the ground metres covered by one pixel there."""
    n = 256 * 2 ** zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return x, y, 156543.03392 * math.cos(math.radians(lat)) / 2 ** zoom


def fetch_elevation(lat: float, lon: float, size: int = 80, cell_m: float = 30.0, zoom: int = TERRAIN_ZOOM) -> np.ndarray:
    """Real elevation in metres for a size x size window centred on (lat, lon), row 0 = south.

    Downloads the few open terrain tiles that cover the window (each pixel encodes metres as R*256 + G + B/256 - 32768),
    stitches them, and samples one value every ``cell_m`` metres with bilinear interpolation.
    """
    cx, cy, mpp = _tile_pixels(lat, lon, zoom)
    step = cell_m / mpp                                   # pixels between neighbouring cells
    offs = (np.arange(size) - (size - 1) / 2.0) * step
    px = cx + offs[None, :] + 0 * offs[:, None]           # columns run west to east
    py = cy - offs[:, None] + 0 * offs[None, :]           # rows run south to north (pixel y grows southwards)
    x0, x1 = int(px.min()) // 256, int(px.max()) // 256
    y0, y1 = int(py.min()) // 256, int(py.max()) // 256
    mosaic = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256))
    for tx in range(x0, x1 + 1):
        for ty in range(y0, y1 + 1):
            r = requests.get(TERRAIN_TILE_URL.format(z=zoom, x=tx, y=ty), timeout=30)
            r.raise_for_status()
            rgb = np.asarray(Image.open(io.BytesIO(r.content)).convert("RGB"), dtype=float)
            mosaic[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = (
                rgb[..., 0] * 256 + rgb[..., 1] + rgb[..., 2] / 256 - 32768)
    return map_coordinates(mosaic, [py - y0 * 256, px - x0 * 256], order=1, mode="nearest")


def load_terrain(region: Region, size: int = 80, cell_m: float = 30.0) -> tuple[np.ndarray, str]:
    """Elevation tile for a region and a label saying where it came from.

    Order: the cached real tile, then a fresh download (which is cached), then the synthetic placeholder if offline.
    """
    safe = "".join(ch if ch.isalnum() else "_" for ch in region.name)
    path = CACHE_DIR / f"dem_{safe}_{size}_{int(cell_m)}.npy"
    if path.exists():
        return np.load(path), REAL_TERRAIN
    try:
        dem = fetch_elevation(region.lat, region.lon, size, cell_m)
    except (requests.RequestException, OSError, ValueError):
        return make_terrain(region, size, cell_m), SYNTHETIC_TERRAIN
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(path, dem)
    return dem, REAL_TERRAIN
