import numpy as np
import pandas as pd
import pytest

from terrapulse import forecast as F
from terrapulse.config import REGIONS, TARGET
from terrapulse.data import synthetic_series


@pytest.fixture(scope="module")
def df():
    return synthetic_series(REGIONS["Hays, Kansas (USA)"], days=900)


def test_features_use_only_the_past(df):
    f = F.make_features(df)
    cut = df.index[500]
    truncated = F.make_features(df.loc[:cut])
    assert np.allclose(f.loc[cut].to_numpy(), truncated.loc[cut].to_numpy())


def test_persistence_returns_last_value(df):
    assert F.PersistenceForecaster().predict(df, 14) == pytest.approx(df[TARGET].iloc[-1])


@pytest.mark.parametrize("name", ["ARIMA", "XGBoost"])
def test_models_predict_valid_wetness(df, name):
    y = F.MODELS[name]().predict(df, 14)
    assert 0.0 <= y <= 1.0


def test_backtest_shape_and_no_leakage(df):
    res = F.backtest(df, 7, model_names=("Persistence",), n_origins=5, step=7)
    assert len(res) == 5
    # the forecast target date is always `horizon` days after its origin
    assert ((res["target_date"] - res["origin"]).dt.days == 7).all()
    # persistence prediction equals the value at the origin, not the target day
    for _, r in res.iterrows():
        assert r["Persistence"] == pytest.approx(df.loc[r["origin"], TARGET])


def test_backtest_rejects_bad_horizon_and_short_history(df):
    with pytest.raises(ValueError):
        F.backtest(df, 0)
    with pytest.raises(ValueError):
        F.backtest(df.iloc[:200], 14)


def test_score_known_values():
    res = pd.DataFrame({"actual": [0.0, 1.0, 2.0], "ARIMA": [0.0, 1.0, 2.0], "XGBoost": [1.0, 2.0, 3.0]})
    s = F.score(res, ["ARIMA", "XGBoost"])
    assert s.loc["ARIMA", "MSE"] == 0.0
    assert s.loc["ARIMA", "R2"] == 1.0
    assert s.loc["XGBoost", "MSE"] == pytest.approx(1.0)
