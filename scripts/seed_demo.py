"""Prepare example records for the demo, so nothing has to be created while recording.

The course asks for several example records to exist before a demo that uses a database. This script asks the running app
(default http://localhost:8088) to simulate a few real fire scenarios and to compute the forecast comparisons, then saves them
through the same API the "Save this run" and "Save comparison to history" buttons use. Nothing is invented: every number is
computed by the models.

    python scripts/seed_demo.py                     # Docker app on port 8088
    python scripts/seed_demo.py http://localhost:8000   # local run

It only adds what is missing (three runs, six model scores), so it is safe to run twice.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8088").rstrip("/")


def call(path: str, body: dict | None = None, timeout: int = 120) -> dict:
    """GET (no body) or POST (JSON body) to the app and return the decoded JSON reply."""
    req = urllib.request.Request(BASE + path, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def save_fire_run(region: str, scenario: dict, hour: float) -> int:
    """Simulate one scenario and keep it in the history exactly as the fire simulator's save button does."""
    sim = call("/api/risk/fire", {"region": region, **scenario})
    t = sim["timeline"]
    idx = min(range(len(t["hours"])), key=lambda i: abs(t["hours"][i] - hour))
    return call("/api/risk/history", {
        "region": region, "forecast_model": sim["wetnessSource"], "forecast_wetness": sim["wetness"], "dryness": sim["dryness"],
        "wind_speed_ms": scenario["wind_kmh"] / 3.6, "wind_toward_deg": scenario["wind_toward_deg"] % 360,
        "ignition_row": scenario["row"], "ignition_col": scenario["col"], "hours": max(t["hours"][idx], 0.25),
        "det_burned_ha": t["detHa"][idx], "prob_burned_ha": t["probHa"][idx], "iou": t["iouDetProb"][idx],
    })["id"]


def save_comparison(region: str, horizon: int = 14, tries: int = 60) -> int:
    """Keep a forecast comparison; the slow backtest runs as a background job, so retry until it is ready."""
    for _ in range(tries):
        try:
            return call("/api/risk/benchmarks", {"region": region, "horizon": horizon})["saved"]
        except urllib.error.HTTPError as e:
            if e.code != 409:
                raise
            time.sleep(2)
    raise SystemExit(f"The forecast comparison for {region} did not finish in time.")


def main() -> None:
    """Seed three fire runs and two forecast comparisons unless the history already has examples."""
    try:
        hist = call("/api/risk/history")
        regions = call("/api/risk/regions")
    except OSError as e:
        raise SystemExit(f"Cannot reach the app at {BASE}: {e}\nStart it first (docker compose up -d).")
    have_runs, have_scores = len(hist["simulations"]) >= 3, len(hist["benchmarks"]) >= 6
    if have_runs and have_scores:
        print(f"History already has {len(hist['simulations'])} saved runs and {len(hist['benchmarks'])} model scores; nothing to do.")
        return
    names = [r["name"] if isinstance(r, dict) else r for r in (regions["regions"] if isinstance(regions, dict) else regions)]
    # the demo starts in Battambang (the default region) and also uses Hays, Kansas
    a = "Battambang, Cambodia" if "Battambang, Cambodia" in names else names[0]
    b = "Hays, Kansas (USA)" if "Hays, Kansas (USA)" in names else names[-1]
    scenarios = [
        (a, dict(wetness_source="manual", manual_wetness=0.30, row=40, col=40, wind_kmh=20, wind_toward_deg=45), 5),
        (a, dict(wetness_source="forecast", forecast_model="XGBoost", row=40, col=40, wind_kmh=20, wind_toward_deg=45), 5),
        (b, dict(wetness_source="manual", manual_wetness=0.25, row=30, col=50, wind_kmh=35, wind_toward_deg=90), 6),
    ]
    if not have_runs:
        for region, sc, hour in scenarios:
            print(f"saved run #{save_fire_run(region, sc, hour)}: {region}, {sc['wetness_source']}, hour {hour}")
    if not have_scores:
        for region in dict.fromkeys([a, b]):
            print(f"saved {save_comparison(region)} model scores for {region}")
    print("Done. The History tab now has example records.")


if __name__ == "__main__":
    main()
