"""TerraPulse dashboard.  Run with:  streamlit run app.py"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from terrapulse import fire
from terrapulse import forecast as F
from terrapulse.config import DEFAULT_HORIZON_DAYS, REGIONS, TARGET, TARGET_LABEL
from terrapulse.data import PowerDataFetcher, load_terrain
from terrapulse.db import Database
from terrapulse.pipeline import N_ORIGINS, cached_backtest

try:  # when run as a page of main.py the page config is already set
    st.set_page_config(page_title="TerraPulse", page_icon="🌍", layout="wide")
except st.errors.StreamlitAPIException:
    pass
CELL_M = 30.0
FLAME_MIN = 45  # minutes a cell is "actively burning" before it counts as burned out


# ----------------------------------------------------------------------------- cached work
@st.cache_resource
def get_db() -> Database:
    """One shared SQLite wrapper for the whole Streamlit session."""
    return Database()


@st.cache_data(show_spinner="Loading satellite reanalysis satellite data...")
def load_data(region_name: str):
    """Daily record for a region (cached) and a label saying where the data came from."""
    fetcher = PowerDataFetcher(REGIONS[region_name])
    df = fetcher.load()
    return df, fetcher.source


@st.cache_data(show_spinner="Running backtest (first time only, ~40 s)...")
def load_backtest(region_name: str, horizon: int):
    """Rolling-origin forecast comparison for a region and horizon (also cached on disk)."""
    df, _ = load_data(region_name)
    return cached_backtest(REGIONS[region_name], df, horizon)


@st.cache_data(show_spinner="Forecasting...")
def forecast_all(region_name: str, horizon: int):
    """Every model's forecast for the chosen horizon, computed once per region and horizon."""
    df, _ = load_data(region_name)
    return {m: F.forecast_now(df, m, horizon) for m in F.MODELS}


@st.cache_data
def terrain(region_name: str):
    """Elevation tile for the region: real open terrain tiles, with a synthetic fallback when offline."""
    return load_terrain(REGIONS[region_name], cell_m=CELL_M)[0]


# ----------------------------------------------------------------------------- sidebar
st.sidebar.title("🌍 TerraPulse")
st.sidebar.caption("Drought forecasting + wildfire spread simulation")
region_name = st.sidebar.selectbox("Region", list(REGIONS), index=list(REGIONS).index("Battambang, Cambodia"))
horizon = st.sidebar.slider("Forecast horizon (days)", 7, 28, DEFAULT_HORIZON_DAYS)
fc_model = st.sidebar.selectbox("Forecast that drives the fire simulation", list(F.MODELS), index=2)
st.sidebar.markdown("---")
st.sidebar.subheader("Fire scenario")
what_if = st.sidebar.checkbox("What-if: set soil wetness by hand", help="Try a dry-season scenario instead of the forecast")
manual_wet = st.sidebar.slider("Soil wetness (0 = dry, 1 = wet)", 0.15, 0.85, 0.30, disabled=not what_if)
wind_kmh = st.sidebar.slider("Wind speed (km/h)", 0, 60, 20)
wind_dir = st.sidebar.slider("Wind blows toward (° compass, 0 = N, 90 = E)", 0, 359, 45)
dem = terrain(region_name)
n = dem.shape[0]
ign_row = st.sidebar.slider("Ignition: north-south position", 0, n - 1, n // 2)
ign_col = st.sidebar.slider("Ignition: east-west position", 0, n - 1, n // 2)
n_runs = st.sidebar.slider("Monte Carlo runs (advanced model)", 10, 100, 40, step=10)

df, source = load_data(region_name)
preds = forecast_all(region_name, horizon)
latest = float(df[TARGET].iloc[-1])
future_date = df.index[-1] + np.timedelta64(horizon, "D")
sim_wetness = manual_wet if what_if else preds[fc_model]
sim_source = "what-if (manual)" if what_if else fc_model
dryness = fire.dryness_from_wetness(sim_wetness)

# ----------------------------------------------------------------------------- header
st.title("TerraPulse")
st.caption(f"{region_name} · data: **{source}**")
if source.startswith("SYNTHETIC"):
    st.warning("Offline: showing synthetic data, not real satellite measurements.")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Soil wetness now", f"{latest:.3f}", help=TARGET_LABEL)
c2.metric(f"Forecast ({fc_model}) for {future_date.date()}", f"{preds[fc_model]:.3f}",
          f"{preds[fc_model] - latest:+.3f}", delta_color="off")
c3.metric("Fuel dryness index", f"{dryness:.2f}",
          help="0 = wet fuel, 1 = very dry fuel; derived from the forecast (or the what-if setting)")
c4.metric("Days of data", f"{len(df):,}")

tab_data, tab_fc, tab_fire, tab_hist = st.tabs(
    ["1 · Data & target", "2 · Forecast comparison", "3 · Fire simulation (3D)", "4 · Saved history"])

# ----------------------------------------------------------------------------- tab 1
with tab_data:
    st.markdown(
        f"**What we predict:** `{TARGET}` = *{TARGET_LABEL}* from satellite reanalysis (MERRA-2), "
        f"**{horizon} days ahead**.  \n"
        "Inputs: past soil wetness, temperature, rainfall, humidity, wind and time of year.")
    recent = df.iloc[-730:]
    fig = go.Figure()
    fig.add_scatter(x=recent.index, y=recent[TARGET], name="Soil wetness", line=dict(color="#2a7f62"))
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="wetness (0–1)")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(df.tail(10).round(3), width="stretch")

# ----------------------------------------------------------------------------- tab 2
with tab_fc:
    st.markdown(
        f"**Experiment 1.** Every model forecasts wetness **{horizon} days ahead** from {N_ORIGINS} weekly "
        "start dates over the past year, and is re-trained each time. Lower error is better.  \n"
        "*Persistence* (\"it stays the same\") is the reference every real model has to beat.")
    results = load_backtest(region_name, horizon)
    scores = F.score(results)
    best = scores["MSE"].idxmin()
    left, right = st.columns([2, 3])
    with left:
        st.dataframe(scores.style.format({"MSE": "{:.5f}", "RMSE": "{:.4f}", "R2": "{:.3f}"})
                     .highlight_min(subset="MSE", color="#cdeccf"), width="stretch")
        st.success(f"Lowest error: **{best}**")
        if st.button("Save this comparison to the database"):
            get_db().save_benchmark(region_name, horizon, scores, len(results), source)
            st.toast("Saved to SQLite")
    with right:
        fig = go.Figure()
        fig.add_scatter(x=results["target_date"], y=results["actual"], name="Actual",
                        line=dict(color="black", width=3))
        for m, col in zip(F.MODELS, ["#999999", "#1f77b4", "#e4572e"]):
            fig.add_scatter(x=results["target_date"], y=results[m], name=m, line=dict(color=col, dash="dot"))
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="wetness (0–1)")
        st.plotly_chart(fig, width="stretch")
    st.markdown(f"**Forecast for {future_date.date()}:** " +
                " · ".join(f"{m} **{v:.3f}**" for m, v in preds.items()))
    st.caption("LSTM neural network: planned as an optional extension, not in Demo 1.")

# ----------------------------------------------------------------------------- tab 3
with tab_fire:
    st.markdown(
        f"Fuel dryness **{dryness:.2f}** comes from the {sim_source} soil wetness ({sim_wetness:.2f}), "
        "so drier soil means a faster fire. Terrain is a synthetic 2.4 km tile (placeholder for a real elevation model).")
    mode = st.radio("Model view", ["Deterministic (required)", "Probabilistic burn chance (advanced)"],
                    horizontal=True)
    hours = st.slider("Time since ignition (hours)", 0.5, 12.0, 4.0, step=0.5)
    t_min = hours * 60

    sc = fire.FireScenario(dem, (ign_row, ign_col), dryness, wind_kmh / 3.6, float(wind_dir), CELL_M)
    arrival = fire.DeterministicFireModel().run(sc)
    prob_model = fire.ProbabilisticFireModel(n_runs=n_runs)
    arrivals = prob_model.run(sc)
    burned = fire.burned_mask(arrival, t_min)
    prob = prob_model.burn_probability(arrivals, t_min)
    prob_mask = prob >= 0.5
    ha = CELL_M**2 / 10_000
    det_ha, prob_ha = burned.sum() * ha, prob_mask.sum() * ha
    agreement = fire.iou(burned, prob_mask)

    elev01 = (dem - dem.min()) / max(np.ptp(dem), 1e-9)
    color = 0.45 * elev01
    if mode.startswith("Deterministic"):
        age = t_min - arrival
        color = np.where(burned & (age <= FLAME_MIN), 0.6, np.where(burned, 1.0, color))
        scale = [[0, "#4f7a3a"], [0.45, "#c2ab72"], [0.451, "#ff7a00"], [0.75, "#ff7a00"],
                 [0.751, "#2e2e2e"], [1, "#2e2e2e"]]
    else:
        color = np.where(prob > 0, 0.5 + 0.5 * prob, color)
        scale = [[0, "#4f7a3a"], [0.45, "#c2ab72"], [0.5, "#ffe08a"], [0.75, "#ff6a00"], [1, "#7a0000"]]
    xs = np.arange(n) * CELL_M
    fig = go.Figure(go.Surface(x=xs, y=xs, z=dem, surfacecolor=color, cmin=0, cmax=1,
                               colorscale=scale, showscale=False, lighting=dict(ambient=0.7, diffuse=0.6)))
    fig.add_scatter3d(x=[ign_col * CELL_M], y=[ign_row * CELL_M], z=[dem[ign_row, ign_col] + 8],
                      mode="markers", marker=dict(size=6, color="red", symbol="diamond"), name="Ignition")
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=0, b=0), showlegend=False,
                      scene=dict(xaxis_title="east (m)", yaxis_title="north (m)", zaxis_title="elevation (m)",
                                 aspectmode="manual", aspectratio=dict(x=1, y=1, z=0.35)))
    st.plotly_chart(fig, width="stretch")
    st.caption("Orange = actively burning · dark = burned out · yellow→red = chance the cell has burned"
               if not mode.startswith("Deterministic") else
               "Orange = actively burning · dark = burned out · green/tan = unburned terrain (by elevation)")

    perimeter = fire.perimeter_km(burned, CELL_M)     # image-processing step: segment the fire front
    patches = fire.count_burn_regions(burned)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Burned area, deterministic", f"{det_ha:,.1f} ha")
    m2.metric("Burned area, probabilistic (≥50% chance)", f"{prob_ha:,.1f} ha")
    m3.metric("Agreement between models (IoU)", f"{agreement:.2f}")
    m4.metric("Fire front length", f"{perimeter:,.1f} km", f"{patches} burned patch" + ("es" if patches != 1 else ""),
              delta_color="off")
    if st.button("Save this simulation run"):
        run_id = get_db().save_simulation(
            region=region_name, forecast_model=sim_source, forecast_wetness=sim_wetness, dryness=dryness,
            wind_speed_ms=wind_kmh / 3.6, wind_toward_deg=float(wind_dir), ignition_row=ign_row,
            ignition_col=ign_col, hours=hours, det_burned_ha=float(det_ha), prob_burned_ha=float(prob_ha),
            iou=float(agreement))
        st.toast(f"Saved run #{run_id}")

# ----------------------------------------------------------------------------- tab 4
with tab_hist:
    st.subheader("Saved simulation runs")
    st.dataframe(get_db().simulations(), width="stretch", hide_index=True)
    st.subheader("Saved forecast comparisons")
    st.dataframe(get_db().benchmarks(), width="stretch", hide_index=True)
