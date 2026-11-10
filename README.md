# TerraPulse (CSCI 601 course project, Demo 1)

Two tools in one app, built on open satellite and reanalysis data:

- **Trend Detective** tests 20 Earth-system variables (1990 to 2025) for any place on Earth: is a rise or fall real or luck?
  Ask a plain question ("Is it getting hotter?") or scan everything. It flags data glitches and compares places on a 3D globe.
- **Risk Lab** forecasts **root-zone soil wetness 14 days ahead** (ARIMA, XGBoost, persistence reference) and simulates wildfire
  spread on 3D terrain with **three models** (deterministic, probabilistic, particle flow).

Stack: **TypeScript + React** front end (Three.js 3D, MapLibre globe, ECharts), **FastAPI** back end, a Streamlit-free Python
analysis package, SQLite, **Docker**.

## Run it (pick one)

| How | Command | Open |
|---|---|---|
| **Docker** (nothing else to install) | `docker compose up --build` | http://localhost:8088 |
| **Local** (Python 3.12; Node only to rebuild the front end) | `.\scripts\start.ps1`  (or `python -m server`) | http://localhost:8000 |
| **Development** (hot reload) | `.\scripts\dev.ps1` | http://localhost:5173 |

Docker publishes on host port **8088** so it cannot clash with another service on 8000 (change with `TERRAPULSE_PORT`).
The image is multi-stage (Node builds the front end, a slim Python image serves it), runs as a **non-root user**, has a
**health check**, and keeps SQLite on a **named volume** so saved runs survive restarts. `web/dist` is prebuilt in the zip,
so the local option works without Node. Interactive API docs: `/docs`.

```bash
docker compose --profile test run --rm tests     # run the Python tests inside a container
.\scripts\test.ps1                               # everything: pytest, tsc strict, vitest, production build
.\scripts\docker.ps1 up|down|reset|test|logs     # Docker helper
python examples/quickstart.py                    # use the statistics as a plain Python library
python scripts/seed_demo.py                      # save example runs and comparisons into the History tab (for demos)
streamlit run main.py                            # the earlier Streamlit prototype, kept as a fallback
```

## How it fits together

```
Browser (React + TypeScript)                       FastAPI (server/)                    terrapulse/ (no web code)
  Trend Detective ─ ECharts, MapLibre globe  ──►   /api/trends/*  ─ caching, gzip ──►   climate.py  data + disk cache
  Risk Lab ─ Three.js terrain, local playback ──►  /api/risk/*    ─ background jobs ──►  trends.py   Mann-Kendall, Sen, FDR, jump test
  state lives in the URL (shareable links)         /api/meta, /api/health               questions.py, narrative.py  explanations
                                                   X-Response-Time-ms on every reply    forecast.py, fire.py        models
                                                                                        db.py                       SQLite
```

Why it is fast and smooth (measured, not claimed):

| What | Result |
|---|---|
| First screen JavaScript | 57 KB gzipped; 3D, globe and charts load only when opened (and the chart code is prefetched while idle) |
| Trend scan of 20 variables (warm) | about 5 ms; payload 8 KB gzipped |
| A full three-model fire simulation | about 0.9 s cold, 40 ms warm; payload 132 KB gzipped |
| Scrubbing or playing the fire timeline | **no network calls**. The server sends arrival times once; recolouring the 6,400 terrain vertices takes **0.12 ms** per frame (1.25 ms for the 24-run Monte Carlo view). 60 fps needs under 16.7 ms |
| Switching variables, places, stages | stale-while-revalidate: previous content stays visible and dims, nothing flashes blank; identical requests are de-duplicated and cached |
| Slow work (52-date ARIMA backtest) | runs in a background job, pre-computed on disk for all 4 regions and horizons 7, 14, 21, 28; the UI polls |

## Instructor feedback on the proposal, and what we did

| Feedback | Response | Where to see it |
|---|---|---|
| "Define the target variable. What exactly is being predicted?" | **Root-zone soil wetness** (`GWETROOT`, 0 to 1), exactly **14 days ahead** (7 to 28). Every model predicts this one number. | Risk Lab header card, `terrapulse/config.py` |
| "Three simulation approaches is too ambitious: one required, a second advanced, a third optional." | **Required**: deterministic grid. **Advanced**: probabilistic Monte Carlo. **Optional**: particle flow, now also implemented. Each carries its tier badge. | Risk Lab > Fire simulator |


The Project page in the app lists the whole proposal as a checklist with honest statuses (done, partly done, optional, not done).

## Trend Detective: method
1. **Annual means** (9+ valid months): whole years cancel the seasonal cycle.
2. **Mann-Kendall** test; variance inflated when year-to-year autocorrelation is itself detectable.
3. **Sen's slope** with a 95% CI from the Mann-Kendall variance (Gilbert 1987); least-squares cross-check.
4. **Benjamini-Hochberg** false-discovery correction across the 20 variables (and across places on the map).
5. **Step-change (Pettitt) check**: flags a record explained better by one sudden jump than by a slope.
6. **Seasonal fingerprint** (trend per calendar month) and **detrended correlations** with physics-based explanations.

Guided questions (8 plus "Surprise me") list clues and which direction counts as "yes"; answers use only clues that are
significant after correction and not suspected data jumps.

Validated by tests: about 5% false alarms on trendless noise, real trends found 95%+ of the time, CI coverage above 90%,
seasons neither create nor hide a trend. The fire models are checked against the analytic circle on flat calm ground
(exact area 49.9 ha: grid 44.7 ha, particle 54.5 ha, so they bracket the truth).

## Code organization
| Layer | Files | Notes |
|---|---|---|
| Analysis library | `terrapulse/` (`climate`, `trends`, `questions`, `narrative`, `forecast`, `fire`, `db`, `variables`) | no web or UI imports; reusable on its own (`examples/quickstart.py`) |
| API | `server/` (`app`, `routes_trends`, `routes_risk`, `serialize`, `state`, `jobs`, `proposal`) | thin: validates, caches, serialises |
| Front end | `web/src/` (`api/` typed client, `lib/` pure maths and formatting, `charts/` pure option builders, `components/`, `pages/`) | strict TypeScript, no `any` in app code |
| Earlier prototype | `main.py`, `views/`, `app.py` (Streamlit) | kept as a fallback |
| Delivery | `Dockerfile`, `docker-compose.yml`, `scripts/` | |

Every public Python function and class has a docstring (186, checked by a script), and every exported TypeScript component and function has a one-line doc comment.

## Reusing the code

The analysis library has no web or UI imports, so it can be used as a whole or one routine at a time. This runs the statistics on any place with no server and no browser (`examples/quickstart.py` is the full version):

```python
from terrapulse import questions, trends
from terrapulse.climate import PLACES, load_monthly
from terrapulse.variables import CODES

place = PLACES["Svalbard, Arctic"]
df = load_monthly(place.lat, place.lon)               # data: 20 monthly variables, 1990-2025
results = trends.scan(df, CODES, 1990, 2025)          # Mann-Kendall, Sen's slope, FDR, jump check
answer = questions.answer(questions.QUESTIONS_BY_ID["hotter"], results)
print(answer.headline)                                 # "Yes, it is warming"
```

| Reusable piece | Where | Use it for |
|---|---|---|
| Trend statistics | `terrapulse/trends.py` | Mann-Kendall, Sen's slope with confidence interval, Benjamini-Hochberg correction, Pettitt step-change test on any yearly series |
| Forecasting | `terrapulse/forecast.py` | ARIMA, XGBoost and persistence models with a leakage-free rolling backtest |
| Fire models | `terrapulse/fire.py` | Deterministic grid, Monte Carlo and particle-flow spread on any elevation array |
| Elevation and data | `terrapulse/data.py`, `climate.py` | Cached data fetching and real elevation tiles with an offline fallback |
| Storage | `terrapulse/db.py` | SQLite history of simulation runs and forecast benchmarks |

## Documentation

- Every public Python function and class has a docstring (186, checked by a script), and every exported TypeScript component and function has a one-line doc comment.
- Each module starts with a docstring that explains what it does and how.
- The API documents itself: run the server and open `/docs`.

## Tests (142)
- **100 Python** (`pytest`): statistics incl. error-rate simulations, guided questions, three fire models, forecasting, database, real elevation tiles (decoding, caching, offline fallback), charts, and the **HTTP API** end to end (every endpoint, error paths, gzip, background jobs, static serving and path safety).
- **42 front end** (`vitest`): formatting, URL state round-trips, fire colour maths, terrain exaggeration, chart configuration, API client (caching, de-duplication, errors).
- `tsc --strict` and the production build run in `scripts/test.ps1`. The Python suite also passes inside Docker.

## Known limitations

- **Reanalysis is not raw observation.** Changes in the observing system can create artificial jumps (the Greenland cloud record jumps around 2002). The detective flags these but cannot prove the cause.
- **Resolution and scope.** Cells are about 50 km wide, 36 years is short, only linear trends are tested, and a trend shows what is changing, not why.
- **Fire model validation.** Terrain is real elevation (open terrain tiles: an 80 × 80 window of 30 m cells per region, cached in `data/cache`; a synthetic tile is used only if the app is offline and nothing is cached). Heights are stretched in the 3D picture only. The fire model is checked against the analytic circle and between the three models, but not yet against real burn perimeters. The spread rate is a simplified empirical form of Rothermel.
- **Forecast comparison.** Differences between models are small in 3 of 4 regions, and one year of test data cannot support strong claims.

## Roadmap

- Vegetation index (NDVI) and satellite-image filtering.
- Validation of the fire model against real burn perimeters.
- LSTM forecasting model (optional). Image processing is currently limited to SciPy morphology (fire-front segmentation, patch counting).
