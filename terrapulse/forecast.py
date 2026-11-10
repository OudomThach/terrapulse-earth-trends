"""Soil-wetness forecasting.

Target   : root-zone soil wetness (GWETROOT, 0..1) exactly ``horizon`` days ahead.
Required : ArimaForecaster      (classical time-series baseline, target history only)
Advanced : XGBoostForecaster    (gradient boosted trees on lags + weather features)
Reference: PersistenceForecaster ("tomorrow = today") - any real model must beat this.
Optional : LSTM (not implemented in Demo 1).
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from .config import TARGET


# --------------------------------------------------------------------------- features
def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """Features known on day t (no future information)."""
    w = df[TARGET]
    f = pd.DataFrame(index=df.index)
    for lag in (0, 1, 3, 7, 14, 30):
        f[f"wet_lag{lag}"] = w.shift(lag)
    f["rain_7d"] = df["PRECTOTCORR"].rolling(7).sum()
    f["rain_30d"] = df["PRECTOTCORR"].rolling(30).sum()
    f["temp_7d"] = df["T2M"].rolling(7).mean()
    f["rh_7d"] = df["RH2M"].rolling(7).mean()
    f["wind_7d"] = df["WS2M"].rolling(7).mean()
    doy = df.index.dayofyear.to_numpy()
    f["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    f["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    return f


# --------------------------------------------------------------------------- models
class Forecaster(ABC):
    """Interface every forecasting model implements, so they can be compared on equal terms."""

    name: str

    @abstractmethod
    def predict(self, history: pd.DataFrame, horizon: int) -> float:
        """Predict wetness ``horizon`` days after the last row of ``history``."""


class PersistenceForecaster(Forecaster):
    """Reference model: the future equals the present. Any real model must beat it."""

    name = "Persistence"

    def predict(self, history, horizon):
        """The latest observed value."""
        return float(history[TARGET].iloc[-1])


class ArimaForecaster(Forecaster):
    """Classical time-series model fitted on the target's own recent history."""

    name = "ARIMA"

    def __init__(self, order=(2, 1, 1), max_history: int = 730):
        """Choose the ARIMA order and how many recent days to fit on."""
        self.order, self.max_history = order, max_history

    def predict(self, history, horizon):
        """Fit on the history and forecast ``horizon`` days ahead; falls back to persistence on failure."""
        from statsmodels.tsa.arima.model import ARIMA

        y = history[TARGET].iloc[-self.max_history:].to_numpy(dtype=float)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fit = ARIMA(y, order=self.order).fit()
                yhat = float(fit.forecast(horizon)[-1])
        except Exception:  # numerical failure: fall back to persistence
            yhat = float(y[-1])
        return float(np.clip(yhat, 0.0, 1.0))


class XGBoostForecaster(Forecaster):
    """Gradient-boosted trees that learn the CHANGE in wetness from lagged values and weather features."""

    name = "XGBoost"

    def __init__(self, n_estimators=150, max_depth=3, learning_rate=0.05, max_rows: int = 3000):
        """Set the tree-ensemble hyper-parameters and the training window."""
        self.params = dict(n_estimators=n_estimators, max_depth=max_depth,
                           learning_rate=learning_rate, subsample=0.8,
                           random_state=0, n_jobs=1)
        self.max_rows = max_rows

    def predict(self, history, horizon):
        """Train on the history, then add the predicted change to today's wetness."""
        from xgboost import XGBRegressor

        feats = make_features(history)
        # Learn the CHANGE in wetness over the horizon, then add it to today's value.
        # (Soil wetness is very persistent, so modelling the change works far better
        # than modelling the absolute level.)
        change = history[TARGET].shift(-horizon) - history[TARGET]
        train = pd.concat([feats, change.rename("y")], axis=1).dropna().iloc[-self.max_rows:]
        model = XGBRegressor(**self.params)
        model.fit(train.drop(columns="y"), train["y"])
        x_now = feats.iloc[[-1]]
        yhat = float(history[TARGET].iloc[-1] + model.predict(x_now)[0])
        return float(np.clip(yhat, 0.0, 1.0))


MODELS: dict[str, type[Forecaster]] = {
    "Persistence": PersistenceForecaster,
    "ARIMA": ArimaForecaster,
    "XGBoost": XGBoostForecaster,
}


# --------------------------------------------------------------------------- evaluation
def backtest(df: pd.DataFrame, horizon: int, model_names=("Persistence", "ARIMA", "XGBoost"),
             n_origins: int = 26, step: int = 7) -> pd.DataFrame:
    """Rolling-origin test: at each origin day, forecast ``horizon`` days ahead and compare
    with what actually happened. Every model is re-fit at every origin (fair comparison)."""
    if horizon < 1:
        raise ValueError("horizon must be at least 1 day")
    last_origin = len(df) - 1 - horizon
    origins = [last_origin - k * step for k in range(n_origins)][::-1]
    if origins[0] < 400:
        raise ValueError("not enough history for this backtest")
    models = {n: MODELS[n]() for n in model_names}
    rows = []
    for o in origins:
        hist = df.iloc[: o + 1]
        row = {"origin": df.index[o], "target_date": df.index[o + horizon],
               "actual": float(df[TARGET].iloc[o + horizon])}
        for n, m in models.items():
            row[n] = m.predict(hist, horizon)
        rows.append(row)
    return pd.DataFrame(rows)


def score(results: pd.DataFrame, model_names=None) -> pd.DataFrame:
    """MSE, RMSE and R-squared per model."""
    names = model_names or [c for c in results.columns if c in MODELS]
    out = []
    y = results["actual"].to_numpy()
    for n in names:
        err = y - results[n].to_numpy()
        mse = float(np.mean(err**2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r2 = 1.0 - float(np.sum(err**2)) / ss_tot if ss_tot > 0 else float("nan")
        out.append({"model": n, "MSE": mse, "RMSE": mse**0.5, "R2": r2})
    return pd.DataFrame(out).set_index("model")


def forecast_now(df: pd.DataFrame, model_name: str, horizon: int) -> float:
    """Forecast wetness `horizon` days after the latest available observation."""
    return MODELS[model_name]().predict(df, horizon)
