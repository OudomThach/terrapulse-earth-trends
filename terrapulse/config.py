"""Project-wide settings: study regions and the forecasting target definition."""

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Overridable so a container can keep the database on a mounted volume.
CACHE_DIR = Path(os.environ.get("TERRAPULSE_CACHE", ROOT / "data" / "cache"))
DB_PATH = Path(os.environ.get("TERRAPULSE_DB", ROOT / "data" / "terrapulse.db"))

# ---- Forecast target (answers "what exactly is being predicted?") -------------
# Target variable : Root Zone Soil Wetness (GWETROOT), satellite reanalysis / MERRA-2.
#                   Unitless fraction 0..1 (0 = bone dry, 1 = saturated).
# Forecast horizon: value at day t + HORIZON_DAYS, predicted from data up to day t.
TARGET = "GWETROOT"
TARGET_LABEL = "Root-zone soil wetness (0 = dry, 1 = saturated)"
DEFAULT_HORIZON_DAYS = 14

# Weather features available to the machine-learning model (all satellite reanalysis daily).
FEATURES = {
    "GWETROOT": "Root zone soil wetness",
    "T2M": "Air temperature at 2 m (C)",
    "PRECTOTCORR": "Precipitation (mm/day)",
    "RH2M": "Relative humidity at 2 m (%)",
    "WS2M": "Wind speed at 2 m (m/s)",
}


@dataclass(frozen=True)
class Region:
    """A Risk Lab study region: coordinates, plus the settings for the synthetic terrain used only when offline."""

    name: str
    lat: float
    lon: float
    relief_m: float   # how hilly the synthetic fallback tile is (real tiles ignore it)
    seed: int         # makes the terrain tile reproducible


REGIONS = {
    r.name: r
    for r in [
        Region("Hays, Kansas (USA)", 38.88, -99.33, 120.0, 11),
        Region("Boulder foothills, Colorado (USA)", 40.01, -105.30, 380.0, 23),
        Region("Central Valley, California (USA)", 36.75, -119.77, 160.0, 37),
        Region("Battambang, Cambodia", 13.10, 103.20, 90.0, 41),
    ]
}
