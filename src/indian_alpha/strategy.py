"""A deliberately simple, explainable, long-only strategy."""

from __future__ import annotations

import pandas as pd


def trend_rsi_signal(
    frame: pd.DataFrame,
    fast_window: int = 20,
    slow_window: int = 50,
    rsi_window: int = 14,
    rsi_entry_floor: float = 50.0,
    rsi_entry_ceiling: float = 70.0,
) -> pd.Series:
    """Hold long when trend is positive and RSI confirms without being overbought.

    This produces a desired end-of-day signal. The backtester shifts it by one
    trading day, preventing same-close look-ahead bias.
    """
    required = [f"sma_{fast_window}", f"sma_{slow_window}", f"rsi_{rsi_window}"]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Strategy is missing feature columns: {sorted(missing)}")
    if not 0 <= rsi_entry_floor < rsi_entry_ceiling <= 100:
        raise ValueError("RSI thresholds must satisfy 0 <= floor < ceiling <= 100.")

    trend_up = frame[f"sma_{fast_window}"] > frame[f"sma_{slow_window}"]
    momentum_ok = frame[f"rsi_{rsi_window}"].between(
        rsi_entry_floor, rsi_entry_ceiling, inclusive="both"
    )
    return (trend_up & momentum_ok).astype(float).rename("signal")

