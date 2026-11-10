"""Risk Lab endpoints: soil-wetness forecasting, three wildfire models, saved history."""

from __future__ import annotations

import base64
from functools import lru_cache
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from terrapulse import fire, forecast as F
from terrapulse.config import DEFAULT_HORIZON_DAYS, REGIONS, TARGET, TARGET_LABEL, Region
from terrapulse.data import PowerDataFetcher, load_terrain
from terrapulse.pipeline import N_ORIGINS, cached_backtest

from . import jobs, state
from .serialize import num, nums

router = APIRouter(prefix="/api/risk", tags=["risk"])

FORECAST_TIERS = {"Persistence": "Reference", "ARIMA": "Required", "XGBoost": "Advanced"}
FIRE_MODELS = [
    {"id": "deterministic", "name": "Deterministic grid", "tier": "Required",
     "summary": "Rothermel-style spread rate turned into arrival times by shortest paths."},
    {"id": "probabilistic", "name": "Probabilistic Monte Carlo", "tier": "Advanced",
     "summary": "The same physics run many times with random wind gusts and patchy fuel."},
    {"id": "particle", "name": "Particle flow", "tier": "Optional",
     "summary": "Front-tracking particles carried outward by the spread rate; no grid bias."},
]
GRID = 80
CELL_M = 30.0
HOURS = np.arange(0.0, 12.01, 0.25)          # timeline resolution for precomputed metrics
QUANTUM_MIN = 5.0                            # ensemble arrival times are sent in 5-minute steps
NEVER = 255


def _region(name: str) -> Region:
    """Look up a Risk Lab region or answer 404."""
    if name not in REGIONS:
        raise HTTPException(404, f"Unknown region '{name}'")
    return REGIONS[name]


@lru_cache(maxsize=16)
def _daily(region_name: str) -> tuple[pd.DataFrame, str]:
    """Daily record for a region and a label for where it came from."""
    fetcher = PowerDataFetcher(REGIONS[region_name])
    df = fetcher.load()
    return df, fetcher.source


@lru_cache(maxsize=128)
def _forecast_value(region_name: str, horizon: int, model: str) -> float:
    """One model's wetness forecast ``horizon`` days after the latest observation."""
    return F.forecast_now(_daily(region_name)[0], model, horizon)


@router.get("/regions")
def regions() -> dict:
    """The study regions and the project's fixed forecast target."""
    return {"regions": [{"name": r.name, "lat": r.lat, "lon": r.lon, "reliefM": r.relief_m} for r in REGIONS.values()],
            "target": {"code": TARGET, "label": TARGET_LABEL}, "defaultHorizon": DEFAULT_HORIZON_DAYS,
            "fireModels": FIRE_MODELS, "forecastTiers": {**FORECAST_TIERS, "LSTM": "Optional (not implemented)"}}


def _overview(region: Region, horizon: int) -> dict:
    """Forecast comparison for one region and horizon (slow the first time: ARIMA refits at every origin)."""
    df, source = _daily(region.name)
    results = cached_backtest(region, df, horizon)
    scores = F.score(results)
    forecasts = {m: _forecast_value(region.name, horizon, m) for m in F.MODELS}
    best = scores["MSE"].idxmin()
    last = df.index[-1]
    recent = df[TARGET].iloc[-730:]
    return {
        "status": "ready", "region": region.name, "horizon": horizon, "target": {"code": TARGET, "label": TARGET_LABEL},
        "dataSource": source, "nOrigins": N_ORIGINS,
        "latest": {"date": last.strftime("%Y-%m-%d"), "value": num(df[TARGET].iloc[-1], 4)},
        "forecastDate": (last + pd.DateOffset(days=horizon)).strftime("%Y-%m-%d"),
        "forecasts": {m: num(v, 4) for m, v in forecasts.items()},
        "models": [{"name": m, "tier": FORECAST_TIERS[m], "mse": num(r.MSE, 6), "rmse": num(r.RMSE, 5),
                    "r2": num(r.R2, 4), "best": m == best} for m, r in scores.iterrows()],
        "backtest": {"targetDates": [d.strftime("%Y-%m-%d") for d in results["target_date"]],
                     "actual": nums(results["actual"], 4), **{m: nums(results[m], 4) for m in F.MODELS}},
        "history": {"dates": [d.strftime("%Y-%m-%d") for d in recent.index], "values": nums(recent, 4)},
    }


@router.get("/overview")
def overview(region: str, horizon: int = Query(DEFAULT_HORIZON_DAYS, ge=7, le=28)) -> dict:
    """Forecast comparison. If the backtest still has to run, answers {status: 'computing'} to poll."""
    r = _region(region)
    done, value = jobs.get_or_start(("overview", region, horizon), lambda: _overview(r, horizon), wait=4.0)
    return value if done else {"status": "computing", "region": region, "horizon": horizon}


class FireRequest(BaseModel):
    """Inputs for one fire simulation."""

    region: str
    row: int = Field(GRID // 2, ge=0, lt=GRID)
    col: int = Field(GRID // 2, ge=0, lt=GRID)
    wind_kmh: float = Field(20.0, ge=0, le=80)
    wind_toward_deg: float = Field(45.0, ge=0, lt=360)
    wetness_source: Literal["forecast", "manual"] = "forecast"
    forecast_model: Literal["Persistence", "ARIMA", "XGBoost"] = "XGBoost"
    manual_wetness: float = Field(0.30, ge=0.05, le=0.95)
    horizon: int = Field(DEFAULT_HORIZON_DAYS, ge=7, le=28)
    n_runs: int = Field(24, ge=8, le=60)


def _timeline(det: np.ndarray, ens: np.ndarray, part: np.ndarray) -> dict:
    """Burned area, fire-front length and model agreement at every quarter hour (computed once on the server)."""
    ha = CELL_M ** 2 / 10_000
    out = {k: [] for k in ("hours", "detHa", "probHa", "partHa", "frontKm", "patches", "iouDetProb", "iouDetPart",
                           "iouProbPart")}
    for h in HOURS:
        t = h * 60.0
        d, p, q = det <= t, (ens <= t).mean(axis=0) >= 0.5, part <= t
        out["hours"].append(float(h))
        out["detHa"].append(round(float(d.sum() * ha), 2))
        out["probHa"].append(round(float(p.sum() * ha), 2))
        out["partHa"].append(round(float(q.sum() * ha), 2))
        out["frontKm"].append(round(fire.perimeter_km(d, CELL_M), 3))
        out["patches"].append(fire.count_burn_regions(d))
        out["iouDetProb"].append(round(fire.iou(d, p), 3))
        out["iouDetPart"].append(round(fire.iou(d, q), 3))
        out["iouProbPart"].append(round(fire.iou(p, q), 3))
    return out


@lru_cache(maxsize=64)
def _fire(region_name: str, row: int, col: int, wind_kmh: float, wind_deg: float, wetness: float, n_runs: int) -> dict:
    """Run all three fire models for one scenario and package the results compactly."""
    dem, terrain_source = load_terrain(REGIONS[region_name], size=GRID, cell_m=CELL_M)
    dryness = fire.dryness_from_wetness(wetness)
    sc = fire.FireScenario(dem, (row, col), dryness, wind_kmh / 3.6, wind_deg, CELL_M)
    det = fire.DeterministicFireModel().run(sc)
    ens = fire.ProbabilisticFireModel(n_runs=n_runs).run(sc)
    part = fire.ParticleFireModel().run(sc)
    quant = np.where(np.isfinite(ens), np.minimum(np.rint(ens / QUANTUM_MIN), NEVER - 1), NEVER).astype(np.uint8)
    return {
        "grid": {"rows": GRID, "cols": GRID, "cellM": CELL_M}, "ignition": {"row": row, "col": col},
        "wind": {"kmh": wind_kmh, "towardDeg": wind_deg}, "wetness": wetness, "dryness": num(dryness, 3),
        "dem": nums(dem.ravel(), 1), "terrainSource": terrain_source,
        "deterministic": nums(det.ravel(), 1), "particle": nums(part.ravel(), 1),
        "ensemble": {"runs": n_runs, "quantumMin": QUANTUM_MIN, "never": NEVER,
                     "data": base64.b64encode(quant.tobytes()).decode("ascii")},
        "timeline": _timeline(det, ens, part),
    }


@router.post("/fire")
def run_fire(req: FireRequest) -> dict:
    """Simulate a fire with the three models. Time scrubbing then happens in the browser."""
    _region(req.region)
    if req.wetness_source == "forecast":
        wetness, source = _forecast_value(req.region, req.horizon, req.forecast_model), f"{req.forecast_model} forecast"
    else:
        wetness, source = req.manual_wetness, "what-if (manual)"
    payload = _fire(req.region, req.row, req.col, round(req.wind_kmh, 1), round(req.wind_toward_deg), round(wetness, 3),
                    req.n_runs)
    return {**payload, "wetnessSource": source, "region": req.region}


class SaveRun(BaseModel):
    """A simulation run the user chose to keep."""

    region: str
    forecast_model: str
    forecast_wetness: float = Field(ge=0, le=1)
    dryness: float = Field(ge=0, le=1)
    wind_speed_ms: float = Field(ge=0)
    wind_toward_deg: float = Field(ge=0, lt=360)
    ignition_row: int = Field(ge=0, lt=GRID)
    ignition_col: int = Field(ge=0, lt=GRID)
    hours: float = Field(gt=0, le=12)
    det_burned_ha: float = Field(ge=0)
    prob_burned_ha: float | None = Field(default=None, ge=0)
    iou: float | None = Field(default=None, ge=0, le=1)


def _records(df: pd.DataFrame) -> list[dict]:
    """DataFrame rows as plain dicts with None for missing values."""
    return df.astype(object).where(df.notna(), None).to_dict(orient="records")


@router.post("/history")
def save_run(run: SaveRun) -> dict:
    """Keep a simulation run in the SQLite history."""
    _region(run.region)
    return {"id": state.db().save_simulation(**run.model_dump())}


class SaveBenchmark(BaseModel):
    """Which forecast comparison to keep."""

    region: str
    horizon: int = Field(DEFAULT_HORIZON_DAYS, ge=7, le=28)


@router.post("/benchmarks")
def save_benchmark(req: SaveBenchmark) -> dict:
    """Keep the current forecast comparison in the SQLite history."""
    r = _region(req.region)
    data = overview(req.region, req.horizon)
    if data.get("status") != "ready":
        raise HTTPException(409, "The comparison is still being computed; try again in a moment.")
    df, source = _daily(req.region)
    scores = F.score(cached_backtest(r, df, req.horizon))
    state.db().save_benchmark(req.region, req.horizon, scores, N_ORIGINS, source)
    return {"saved": len(scores)}


@router.get("/history")
def history() -> dict:
    """Saved simulation runs and forecast comparisons, newest first."""
    return {"simulations": _records(state.db().simulations()), "benchmarks": _records(state.db().benchmarks())}
