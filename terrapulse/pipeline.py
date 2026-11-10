"""Glue between data, forecasting and storage, with a disk cache for the slow backtest."""

from __future__ import annotations

import pandas as pd

from . import forecast as F
from .config import CACHE_DIR, Region
from .data import PowerDataFetcher
from .db import Database

N_ORIGINS = 52  # one year of weekly forecast origins


def _backtest_file(region: Region, horizon: int):
    tag = f"{region.lat:.2f}_{region.lon:.2f}".replace("-", "m")
    return CACHE_DIR / f"backtest_{tag}_h{horizon}.csv"


def cached_backtest(region: Region, df: pd.DataFrame, horizon: int, refresh: bool = False) -> pd.DataFrame:
    """Rolling-origin backtest, saved to disk because ARIMA refits make it take ~40 s."""
    path = _backtest_file(region, horizon)
    if path.exists() and not refresh:
        return pd.read_csv(path, parse_dates=["origin", "target_date"])
    res = F.backtest(df, horizon, n_origins=N_ORIGINS)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    res.to_csv(path, index=False)
    return res


def run_benchmark(region: Region, horizon: int, db: Database | None = None, refresh: bool = False):
    """Load data, run (or reuse) the backtest, store scores in SQLite, return everything."""
    fetcher = PowerDataFetcher(region)
    df = fetcher.load()
    results = cached_backtest(region, df, horizon, refresh=refresh)
    scores = F.score(results)
    if db is not None:
        db.save_benchmark(region.name, horizon, scores, len(results), fetcher.source)
    return df, results, scores, fetcher.source
