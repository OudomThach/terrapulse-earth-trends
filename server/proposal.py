"""The instructor's feedback and the proposal's requirements, mapped to where each is met (shown in the UI).

Statuses are deliberately honest: ``done``, ``partial``, ``optional`` (allowed to skip by the instructor)
or ``todo``.
"""

FEEDBACK = [
    {
        "id": "target",
        "instructor": "The forecasting portion needs clarification: define the target variable. "
                      "What exactly is being predicted?",
        "response": "The target is root-zone soil wetness (GWETROOT, a 0 to 1 fraction), predicted exactly "
                    "14 days ahead (adjustable 7 to 28). It is shown at the top of the Risk Lab and fixed in "
                    "terrapulse/config.py. ARIMA, XGBoost and a persistence reference all predict this one number.",
        "status": "done",
        "where": "Risk Lab > Forecast",
    },
    {
        "id": "simulation",
        "instructor": "Three simulation approaches may be too ambitious. Required: one robust model. "
                      "Advanced: a second for comparison. Optional: a third if time permits.",
        "response": "Required: deterministic Rothermel-style grid model (validated against the analytic circle on flat "
                    "ground). Advanced: probabilistic Monte Carlo ensemble. Optional: particle-flow model, now also "
                    "implemented. The three are compared on burned area, fire-front length and IoU agreement.",
        "status": "done",
        "where": "Risk Lab > Fire simulator",
    },
]

REQUIREMENTS = [
    {"item": "Fetch open satellite data", "status": "done", "where": "terrapulse/climate.py, data.py"},
    {"item": "Forecast with ARIMA (required) and XGBoost (advanced)", "status": "done", "where": "Risk Lab > Forecast"},
    {"item": "LSTM neural network", "status": "optional", "where": "Not implemented; optional per the instructor. Planned for the final demo (Dec 3) if time allows"},
    {"item": "Fire spread on 3D terrain, with a time slider", "status": "done", "where": "Risk Lab > Fire simulator"},
    {"item": "Terrain from a real elevation model", "status": "done", "where": "Risk Lab > Fire simulator (open terrain tiles, cached; synthetic only if offline)"},
    {"item": "Validate the fire model against real burn perimeters", "status": "partial",
     "where": "Checked against the analytic circle and between models; no real perimeters yet. Planned for the final demo (Dec 3)"},
    {"item": "Image processing: segment hazard perimeters (SciPy)", "status": "done",
     "where": "terrapulse/fire.py (erosion, labelling)"},
    {"item": "NDVI and satellite-image filtering", "status": "todo", "where": "Not implemented. Planned for the final demo (Dec 3)"},
    {"item": "SQLite storage of runs and benchmarks", "status": "done", "where": "Risk Lab > History"},
    {"item": "Automated tests (pytest)", "status": "done", "where": "tests/ (statistics, fire, forecast, API)"},
    {"item": "Interactive web dashboard", "status": "done", "where": "This TypeScript app"},
    {"item": "Long-term trend analysis with significance tests", "status": "done", "where": "Trend Detective"},
]
