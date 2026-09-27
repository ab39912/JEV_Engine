import numpy as np

from indian_alpha.data import make_demo_data
from indian_alpha.features import add_features, rsi


def test_features_exist_and_volatility_is_annualised():
    frame = make_demo_data(periods=100)
    result = add_features(frame, fast_window=10, slow_window=20)
    expected = {
        "return_1d",
        "log_return_1d",
        "sma_10",
        "sma_20",
        "ema_10",
        "ema_20",
        "rsi_14",
        "volatility_20",
        "volume_sma_20",
        "volume_ratio_20",
        "dollar_volume",
    }
    assert expected.issubset(result.columns)
    manual = result["return_1d"].rolling(20).std() * np.sqrt(252)
    assert np.allclose(result["volatility_20"].dropna(), manual.dropna())


def test_rsi_reaches_100_for_persistent_gains():
    close = make_demo_data(periods=30)["Close"].sort_index()
    close.iloc[:] = np.arange(1, 31, dtype=float)
    assert rsi(close, 14).iloc[-1] == 100.0

