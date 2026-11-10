"""End-to-end tests of the HTTP API (real analysis code, cached data; no mocks of the logic under test)."""

import base64
import time

import pytest
from fastapi.testclient import TestClient

from server import jobs, state
from server.app import create_app
from terrapulse.db import Database

SVALBARD = {"place": "Svalbard, Arctic"}
FIRE = {"region": "Battambang, Cambodia", "wetness_source": "manual", "manual_wetness": 0.3, "row": 40, "col": 40,
        "wind_kmh": 20, "wind_toward_deg": 45}


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


# ------------------------------------------------------------------ meta & plumbing
def test_health_and_timing_header(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert float(r.headers["X-Response-Time-ms"]) >= 0
    assert r.headers["Cache-Control"] == "no-store"


def test_meta_contains_catalog_questions_and_honest_project_status(client):
    m = client.get("/api/meta").json()
    assert len(m["variables"]) == 20 and len(m["places"]) == 19 and len(m["questions"]) == 8
    assert m["years"] == {"first": 1990, "last": 2025}
    assert {f["id"] for f in m["feedback"]} == {"target", "simulation"}
    statuses = {r["status"] for r in m["requirements"]}
    assert statuses <= {"done", "partial", "optional", "todo"} and "todo" in statuses   # nothing is overclaimed


def test_large_responses_are_gzip_compressed(client):
    r = client.get("/api/trends/scan", params=SVALBARD, headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"


# ------------------------------------------------------------------ trends
def test_scan_returns_every_variable_with_corrected_p_values(client):
    r = client.get("/api/trends/scan", params=SVALBARD).json()
    assert len(r["results"]) == 20 and r["summary"]["tested"] == 20
    t2m = next(x for x in r["results"] if x["code"] == "T2M")
    assert t2m["usable"] and t2m["direction"] == "rising" and t2m["label"] in ("Strong evidence", "Significant")
    assert t2m["q"] >= t2m["p"] and t2m["ciLow"] < t2m["perDecade"] < t2m["ciHigh"]
    assert len(t2m["annual"]["years"]) == len(t2m["annual"]["values"]) == 36


def test_scan_input_validation(client):
    assert client.get("/api/trends/scan", params={"place": "Atlantis"}).status_code == 404
    assert client.get("/api/trends/scan").status_code == 422                                   # no place at all
    assert client.get("/api/trends/scan", params={**SVALBARD, "start": 2020, "end": 2025}).status_code == 422
    assert client.get("/api/trends/scan", params={"lat": 95, "lon": 0}).status_code == 422
    assert client.get("/api/trends/scan", params={**SVALBARD, "start": 1980}).status_code == 422


def test_custom_coordinates_work_for_a_cached_spot(client):
    r = client.get("/api/trends/scan", params={"lat": 13.1, "lon": 103.2})
    assert r.status_code == 200 and r.json()["place"]["name"].startswith("Custom")


def test_series_arrays_are_consistent_and_the_wedge_brackets_the_trend(client):
    s = client.get("/api/trends/series", params={**SVALBARD, "code": "T2M_MIN"}).json()
    m = s["monthly"]
    n = len(m["dates"])
    assert n == 432 and all(len(m[k]) == n for k in ("values", "anomalies", "smooth", "trend", "wedgeLow", "wedgeHigh"))
    assert all(lo <= t <= hi + 1e-9 for lo, t, hi in zip(m["wedgeLow"], m["trend"], m["wedgeHigh"]))
    assert len(s["seasonal"]) == 12 and s["verdict"]["tone"] in ("strong", "sig")
    assert s["variable"]["name"] == "Night-time low"


def test_series_for_an_untestable_variable_explains_why(client):
    s = client.get("/api/trends/series", params={"place": "Borneo rainforest", "code": "SNODP"}).json()
    assert s["usable"] is False and s["reason"]


def test_the_data_glitch_case_is_flagged_and_unknown_variables_404(client):
    s = client.get("/api/trends/series", params={"place": "Greenland ice sheet", "code": "CLOUD_AMT"}).json()
    assert s["trend"]["jump"]["suspicious"] and s["jumpWarning"] and "2002" in s["jumpWarning"]
    retested = client.get("/api/trends/series", params={"place": "Greenland ice sheet", "code": "CLOUD_AMT",
                                                        "start": 2002}).json()
    assert retested["trend"]["p"] > 0.5 and not retested["trend"]["jump"]["suspicious"]   # the trend was the glitch
    assert client.get("/api/trends/series", params={**SVALBARD, "code": "NOPE"}).status_code == 404


def test_guided_questions(client):
    a = client.get("/api/trends/answer", params={**SVALBARD, "question": "hotter"}).json()
    assert a["outcome"] == "up" and a["headline"] == "Yes, it is warming" and a["codes"]
    s = client.get("/api/trends/answer", params={**SVALBARD, "question": "surprise"}).json()
    assert len(s["codes"]) == 3
    assert client.get("/api/trends/answer", params={**SVALBARD, "question": "nope"}).status_code == 404


def test_regional_finds_opposite_stories_and_ranks_all_places(client):
    r = client.get("/api/trends/regional", params={"place": "Delhi & Gangetic plain", "code": "ALLSKY_SFC_SW_DWN"}).json()
    assert len(r["rows"]) == 19 and r["finding"]["kind"] == "opposite"
    assert r["finding"]["rising"] > 0 and r["finding"]["falling"] > 0
    assert all(row["q"] >= row["p"] - 1e-9 for row in r["rows"])


def test_correlations_report_and_events(client, monkeypatch):
    c = client.get("/api/trends/correlations", params={"place": "Delhi & Gangetic plain"}).json()
    assert len(c["matrix"]) == len(c["codes"]) and 15 <= len(c["codes"]) <= 20      # variables that never change are left out
    assert "SNODP" not in c["codes"] and c["matrix"][0][0] == pytest.approx(1.0)
    assert c["links"] and c["story"]
    rep = client.get("/api/trends/report", params=SVALBARD)
    assert rep.headers["content-type"].startswith("text/markdown") and "attachment" in rep.headers["content-disposition"]
    assert rep.text.startswith("# Trend Detective case file")
    import pandas as pd
    monkeypatch.setattr(state, "events", lambda: pd.DataFrame([{"title": "t", "category": "Wildfires", "date": "2026-01-01",
                                                                  "lat": 1.0, "lon": 2.0}]))
    assert client.get("/api/trends/events").json()["events"][0]["category"] == "Wildfires"


def test_event_feed_outage_is_a_clean_503(client, monkeypatch):
    def boom():
        raise RuntimeError("offline")
    monkeypatch.setattr(state, "events", boom)
    assert client.get("/api/trends/events").status_code == 503


# ------------------------------------------------------------------ risk lab
def test_risk_regions_state_the_target_and_tiers(client):
    r = client.get("/api/risk/regions").json()
    assert r["target"]["code"] == "GWETROOT" and r["defaultHorizon"] == 14
    assert [m["tier"] for m in r["fireModels"]] == ["Required", "Advanced", "Optional"]
    assert r["forecastTiers"]["ARIMA"] == "Required" and r["forecastTiers"]["LSTM"].startswith("Optional")


def poll_overview(client, params, timeout=60):
    """Poll like the web app does: 'computing' means the work continues in the background."""
    deadline = time.time() + timeout
    while True:
        o = client.get("/api/risk/overview", params=params).json()
        if o["status"] == "ready" or time.time() > deadline:
            return o
        time.sleep(0.5)


def test_overview_compares_models_on_the_same_target(client):
    o = poll_overview(client, {"region": "Battambang, Cambodia", "horizon": 14})
    assert o["status"] == "ready" and {m["name"] for m in o["models"]} == {"Persistence", "ARIMA", "XGBoost"}
    assert sum(m["best"] for m in o["models"]) == 1 and len(o["backtest"]["actual"]) == o["nOrigins"]
    assert all(0 <= v <= 1 for v in o["forecasts"].values())
    assert client.get("/api/risk/overview", params={"region": "Mars", "horizon": 14}).status_code == 404
    assert client.get("/api/risk/overview", params={"region": "Battambang, Cambodia", "horizon": 99}).status_code == 422


def test_fire_payload_is_complete_consistent_and_compact(client):
    r = client.post("/api/risk/fire", json=FIRE).json()
    cells = r["grid"]["rows"] * r["grid"]["cols"]
    assert len(r["dem"]) == len(r["deterministic"]) == len(r["particle"]) == cells == 6400
    assert len(base64.b64decode(r["ensemble"]["data"])) == r["ensemble"]["runs"] * cells
    ign = r["ignition"]["row"] * 80 + r["ignition"]["col"]
    assert r["deterministic"][ign] == 0.0 and r["particle"][ign] == 0.0
    t = r["timeline"]
    assert len(t["hours"]) == 49 and t["hours"][-1] == 12.0
    for k in ("detHa", "probHa", "partHa"):
        assert t[k] == sorted(t[k]) and t[k][-1] > t[k][0]            # fires only grow
    assert all(0 <= v <= 1 for v in t["iouDetProb"] + t["iouDetPart"])
    assert r["wetnessSource"].startswith("what-if")


def test_drier_fuel_burns_more_and_forecast_source_is_recorded(client):
    wet = client.post("/api/risk/fire", json={**FIRE, "manual_wetness": 0.7}).json()
    dry = client.post("/api/risk/fire", json={**FIRE, "manual_wetness": 0.2}).json()
    assert dry["timeline"]["detHa"][24] > wet["timeline"]["detHa"][24]
    f = client.post("/api/risk/fire", json={**FIRE, "wetness_source": "forecast", "forecast_model": "Persistence"}).json()
    assert f["wetnessSource"] == "Persistence forecast" and 0 <= f["wetness"] <= 1


def test_fire_rejects_bad_inputs(client):
    assert client.post("/api/risk/fire", json={**FIRE, "row": 999}).status_code == 422
    assert client.post("/api/risk/fire", json={**FIRE, "wind_kmh": -5}).status_code == 422
    assert client.post("/api/risk/fire", json={**FIRE, "region": "Mars"}).status_code == 404
    assert client.post("/api/risk/fire", json={**FIRE, "wetness_source": "magic"}).status_code == 422


def test_history_roundtrip(client, monkeypatch, tmp_path):
    monkeypatch.setattr(state, "_DB", Database(tmp_path / "history.db"))      # a real file, as in production
    run = {"region": "Battambang, Cambodia", "forecast_model": "what-if (manual)", "forecast_wetness": 0.3, "dryness": 0.83,
           "wind_speed_ms": 5.5, "wind_toward_deg": 45, "ignition_row": 40, "ignition_col": 40, "hours": 5,
           "det_burned_ha": 120.5, "prob_burned_ha": 130.0, "iou": 0.88}
    saved = client.post("/api/risk/history", json=run).json()
    assert saved["id"] == 1
    poll_overview(client, {"region": "Battambang, Cambodia", "horizon": 14})
    assert client.post("/api/risk/benchmarks", json={"region": "Battambang, Cambodia", "horizon": 14}).json()["saved"] == 3
    h = client.get("/api/risk/history").json()
    assert h["simulations"][0]["det_burned_ha"] == 120.5 and len(h["benchmarks"]) == 3
    assert client.post("/api/risk/history", json={**run, "hours": 99}).status_code == 422


# ------------------------------------------------------------------ background jobs & static serving
def test_job_runner_answers_fast_work_immediately_and_slow_work_later():
    done, value = jobs.get_or_start(("t", "fast"), lambda: 42, wait=2)
    assert done and value == 42
    done, _ = jobs.get_or_start(("t", "slow"), lambda: time.sleep(0.4) or "ok", wait=0.01)
    assert not done
    done, value = jobs.get_or_start(("t", "slow"), lambda: "never runs again", wait=3)
    assert done and value == "ok"


def test_failed_jobs_can_be_retried():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("first attempt fails")
        return "recovered"

    with pytest.raises(RuntimeError):
        jobs.get_or_start(("t", "flaky"), flaky, wait=2)
    assert jobs.get_or_start(("t", "flaky"), flaky, wait=2) == (True, "recovered")


def test_built_web_app_is_served_with_spa_fallback_and_safe_paths(tmp_path, monkeypatch):
    import server.app as app_module
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "index.html").write_text("<html>shell</html>")
    (tmp_path.parent / "secret.txt").write_text("top secret")
    monkeypatch.setattr(app_module, "WEB_DIST", tmp_path)
    c = TestClient(app_module.create_app())
    assert "shell" in c.get("/").text and "shell" in c.get("/some/client/route").text
    asset = c.get("/assets/app.js")
    assert asset.status_code == 200 and "immutable" in asset.headers["cache-control"]
    assert c.get("/api/health").json()["status"] == "ok"                       # API still wins over the SPA fallback
    assert "top secret" not in c.get("/%2e%2e/secret.txt").text and "top secret" not in c.get("/../secret.txt").text


def test_without_a_build_the_root_explains_how_to_build(tmp_path, monkeypatch):
    import server.app as app_module
    monkeypatch.setattr(app_module, "WEB_DIST", tmp_path / "missing")
    assert "npm run build" in TestClient(app_module.create_app()).get("/").json()["message"]
