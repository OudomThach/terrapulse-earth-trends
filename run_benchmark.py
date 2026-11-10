"""Pre-compute the forecast comparison for every region so the demo is instant.

    python run_benchmark.py            # all regions, 14-day horizon
    python run_benchmark.py 7 28       # custom horizons
"""

import sys

from terrapulse.config import DEFAULT_HORIZON_DAYS, REGIONS
from terrapulse.db import Database
from terrapulse.pipeline import run_benchmark

if __name__ == "__main__":
    horizons = [int(a) for a in sys.argv[1:]] or [DEFAULT_HORIZON_DAYS]
    db = Database()
    for region in REGIONS.values():
        for h in horizons:
            _, _, scores, src = run_benchmark(region, h, db)
            print(f"\n{region.name} | horizon {h} d | {src}")
            print(scores.round(4).to_string())
