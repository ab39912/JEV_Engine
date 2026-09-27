"""Technical features implemented directly with pandas for transparency."""

from __future__ import annotations

import numpy as np
import pandas as pd


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Wilder-style Relative Strength Index using exponentially smoothed gains/losses."""
    if window < 2:
        raise ValueError("RSI window must be at least 2.")
    change = close.diff()
    gain = change.clip(lower=0.0)
    loss = -change.clip(upper=0.0)
    average_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    average_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    relative_strength = average_gain / average_loss.replace(0.0, np.nan)
    result = 100.0 - (100.0 / (1.0 + relative_strength))
    result = result.mask((average_loss == 0) & (average_gain > 0), 100.0)
    result = result.mask((average_loss == 0) & (average_gain == 0), 50.0)
    return result.rename(f"rsi_{window}")


def add_features(
    frame: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    rsi_window: int = 14,
    volatility_window: int = 20,
    volume_window: int = 20,
) -> pd.DataFrame:
    """Add returns, trend, momentum, volatility, and volume features."""
    if not 1 < fast_window < slow_window:
        raise ValueError("Require 1 < fast_window < slow_window.")
    data = frame.copy()
    close = data["Close"]
    volume = data["Volume"]

    data["return_1d"] = close.pct_change()
    data["log_return_1d"] = np.log(close / close.shift(1))
    data[f"sma_{fast_window}"] = close.rolling(fast_window).mean()
    data[f"sma_{slow_window}"] = close.rolling(slow_window).mean()
    data[f"ema_{fast_window}"] = close.ewm(span=fast_window, adjust=False).mean()
    data[f"ema_{slow_window}"] = close.ewm(span=slow_window, adjust=False).mean()
    data[f"rsi_{rsi_window}"] = rsi(close, rsi_window)
    data[f"volatility_{volatility_window}"] = (
        data["return_1d"].rolling(volatility_window).std() * np.sqrt(252)
    )
    data[f"volume_sma_{volume_window}"] = volume.rolling(volume_window).mean()
    data[f"volume_ratio_{volume_window}"] = volume / data[f"volume_sma_{volume_window}"]
    data["dollar_volume"] = close * volume
    return data

