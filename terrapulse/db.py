"""SQLite storage for forecast benchmarks and simulation runs (Module 6)."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS forecast_benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    region TEXT NOT NULL,
    horizon_days INTEGER NOT NULL,
    model TEXT NOT NULL,
    mse REAL NOT NULL,
    rmse REAL NOT NULL,
    r2 REAL,
    n_origins INTEGER NOT NULL,
    data_source TEXT
);
CREATE TABLE IF NOT EXISTS simulation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    region TEXT NOT NULL,
    forecast_model TEXT,
    forecast_wetness REAL,
    dryness REAL NOT NULL,
    wind_speed_ms REAL NOT NULL,
    wind_toward_deg REAL NOT NULL,
    ignition_row INTEGER NOT NULL,
    ignition_col INTEGER NOT NULL,
    hours REAL NOT NULL,
    det_burned_ha REAL NOT NULL,
    prob_burned_ha REAL,
    iou REAL
);
"""


class Database:
    """Small SQLite store for forecast benchmarks and simulation runs."""

    def __init__(self, path: str | Path = DB_PATH):
        """Open (or create) the database file and make sure the tables exist; ':memory:' is allowed for tests."""
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._memory_conn = sqlite3.connect(":memory:") if self.path == ":memory:" else None
        with self._conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = self._memory_conn or sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if self._memory_conn is None:
                conn.close()

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def save_benchmark(self, region: str, horizon: int, scores: pd.DataFrame,
                       n_origins: int, data_source: str) -> None:
        """Store one forecast comparison, one row per model."""
        with self._conn() as c:
            c.executemany(
                "INSERT INTO forecast_benchmarks (created_at, region, horizon_days, model, mse, rmse, r2,"
                " n_origins, data_source) VALUES (?,?,?,?,?,?,?,?,?)",
                [(self._now(), region, horizon, m, r.MSE, r.RMSE, None if pd.isna(r.R2) else r.R2,
                  n_origins, data_source) for m, r in scores.iterrows()])

    def save_simulation(self, **f) -> int:
        """Store one fire simulation run and return its id."""
        cols = ("region", "forecast_model", "forecast_wetness", "dryness", "wind_speed_ms",
                "wind_toward_deg", "ignition_row", "ignition_col", "hours", "det_burned_ha",
                "prob_burned_ha", "iou")
        with self._conn() as c:
            cur = c.execute(
                f"INSERT INTO simulation_runs (created_at, {', '.join(cols)}) "
                f"VALUES (?, {', '.join('?' * len(cols))})",
                (self._now(), *[f.get(k) for k in cols]))
            return cur.lastrowid

    def benchmarks(self, limit: int = 50) -> pd.DataFrame:
        """Most recent saved forecast comparisons, newest first."""
        with self._conn() as c:
            return pd.read_sql_query(
                "SELECT * FROM forecast_benchmarks ORDER BY id DESC LIMIT ?", c, params=(limit,))

    def simulations(self, limit: int = 50) -> pd.DataFrame:
        """Most recent saved fire simulation runs, newest first."""
        with self._conn() as c:
            return pd.read_sql_query(
                "SELECT * FROM simulation_runs ORDER BY id DESC LIMIT ?", c, params=(limit,))
