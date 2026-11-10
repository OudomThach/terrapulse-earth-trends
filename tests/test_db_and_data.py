import numpy as np
import pandas as pd
import pytest

from terrapulse.config import REGIONS
from terrapulse.data import make_terrain, parse_power_json
from terrapulse.db import Database


def test_database_roundtrip():
    db = Database(":memory:")
    scores = pd.DataFrame({"MSE": [0.01], "RMSE": [0.1], "R2": [0.9]}, index=pd.Index(["ARIMA"], name="model"))
    db.save_benchmark("Hays", 14, scores, 52, "test")
    b = db.benchmarks()
    assert len(b) == 1 and b.loc[0, "model"] == "ARIMA" and b.loc[0, "horizon_days"] == 14

    run_id = db.save_simulation(region="Hays", forecast_model="ARIMA", forecast_wetness=0.4, dryness=0.7,
                                wind_speed_ms=5.0, wind_toward_deg=45.0, ignition_row=1, ignition_col=2,
                                hours=4.0, det_burned_ha=12.5, prob_burned_ha=13.0, iou=0.9)
    s = db.simulations()
    assert run_id == 1 and len(s) == 1 and s.loc[0, "det_burned_ha"] == 12.5


def test_database_rejects_missing_required_field():
    db = Database(":memory:")
    with pytest.raises(Exception):
        db.save_simulation(region="Hays")  # dryness etc. are NOT NULL


def test_parse_power_json_handles_fill_values():
    payload = {"properties": {"parameter": {
        "GWETROOT": {"20260101": 0.4, "20260102": -999.0, "20260103": 0.42},
        "T2M": {"20260101": 5.0, "20260102": 6.0, "20260103": 7.0}}}}
    df = parse_power_json(payload)
    assert list(df.index) == list(pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]))
    assert df["GWETROOT"].iloc[1] == pytest.approx(0.41)  # short gap interpolated, no -999 left
    assert (df != -999.0).all().all()


def test_terrain_is_reproducible_and_matches_relief():
    r = REGIONS["Boulder foothills, Colorado (USA)"]
    a, b = make_terrain(r), make_terrain(r)
    assert np.array_equal(a, b)
    assert a.shape == (80, 80)
    assert np.ptp(a) == pytest.approx(r.relief_m)


# ---------------------------------------------------------------------------- real elevation tiles
def _fake_tile_response(metres_of: "callable"):
    """A fake HTTP reply holding a 256 x 256 terrain tile whose elevation at pixel (row, col) is metres_of(row, col)."""
    import io
    from PIL import Image

    rows, cols = np.mgrid[0:256, 0:256]
    m = metres_of(rows, cols) + 32768.0
    r, g = np.floor(m / 256), np.floor(m % 256)
    b = np.floor((m - np.floor(m)) * 256)
    img = Image.fromarray(np.stack([r, g, b], axis=-1).astype(np.uint8), "RGB")
    buf = io.BytesIO()
    img.save(buf, "PNG")

    class Reply:
        content = buf.getvalue()

        def raise_for_status(self):
            return None

    return Reply()


def test_fetch_elevation_decodes_metres_and_puts_north_at_the_top_row(monkeypatch):
    from terrapulse import data

    # a plane that rises 1 m per pixel going north (pixel rows count downwards, so elevation falls as row grows)
    monkeypatch.setattr(data.requests, "get", lambda url, timeout=30: _fake_tile_response(lambda r, c: 1000.0 - r))
    dem = data.fetch_elevation(13.1, 103.2, size=20, cell_m=30.0)
    assert dem.shape == (20, 20)
    assert 800 < dem.min() and dem.max() < 1000        # decoded to plausible metres, not raw colour values
    assert dem[-1].mean() > dem[0].mean()               # row 0 is the south edge, the last row is the north edge
    assert np.allclose(dem[:, 0], dem[:, -1], atol=1e-6)  # nothing varies east-west in this fake plane


def test_load_terrain_uses_real_tiles_caches_them_and_falls_back_when_offline(monkeypatch, tmp_path):
    from terrapulse import data

    monkeypatch.setattr(data, "CACHE_DIR", tmp_path)
    region = data.Region("Test place", 10.0, 20.0, 50.0, 3)
    calls = []
    monkeypatch.setattr(data.requests, "get", lambda url, timeout=30: calls.append(url) or _fake_tile_response(lambda r, c: 300.0 + 0 * r))
    dem, source = data.load_terrain(region, size=16)
    assert source == data.REAL_TERRAIN and np.allclose(dem, 300.0, atol=0.01)
    n = len(calls)
    assert data.load_terrain(region, size=16)[1] == data.REAL_TERRAIN and len(calls) == n   # second time: from the cache, no download

    def offline(url, timeout=30):
        raise data.requests.ConnectionError("no network")

    monkeypatch.setattr(data.requests, "get", offline)
    other = data.Region("Another place", 11.0, 21.0, 50.0, 4)
    dem2, source2 = data.load_terrain(other, size=16)
    assert source2 == data.SYNTHETIC_TERRAIN and dem2.shape == (16, 16)
