"""Vectorised, long-only daily backtester with explicit transaction costs."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass(frozen=True)
class BacktestMetrics:
    start_date: str
    end_date: str
    observations: int
    total_return: float
    gross_total_return: float
    cagr: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    number_of_trades: int
    transaction_costs_paid: float
    benchmark_total_return: float

    def to_dict(self) -> dict[str, str | int | float]:
        return asdict(self)


@dataclass(frozen=True)
class BacktestResult:
    daily: pd.DataFrame
    trades: pd.DataFrame
    metrics: BacktestMetrics


def _trade_log(daily: pd.DataFrame) -> pd.DataFrame:
    """Build completed round-trip trades from the executed position series."""
    records: list[dict[str, object]] = []
    entry_date: pd.Timestamp | None = None
    trade_returns: list[float] = []

    for date, row in daily.iterrows():
        turnover = row["turnover"]
        if row["position"] == 1 and turnover > 0 and entry_date is None:
            entry_date = pd.Timestamp(date)
            trade_returns = [float(row["strategy_return"])]
        elif row["position"] == 1 and entry_date is not None:
            trade_returns.append(float(row["strategy_return"]))
        elif row["position"] == 0 and turnover > 0 and entry_date is not None:
            # Include the exit cost, which occurs on the first flat day.
            trade_returns.append(float(row["strategy_return"]))
            records.append(
                {
                    "entry_date": entry_date,
                    "exit_date": pd.Timestamp(date),
                    "return": float(np.prod(1.0 + np.asarray(trade_returns)) - 1.0),
                    "holding_days": (pd.Timestamp(date) - entry_date).days,
                }
            )
            entry_date = None
            trade_returns = []

    return pd.DataFrame(records, columns=["entry_date", "exit_date", "return", "holding_days"])


def run_backtest(
    frame: pd.DataFrame,
    signal: pd.Series,
    initial_capital: float = 100_000.0,
    transaction_cost_bps: float = 10.0,
    annual_risk_free_rate: float = 0.0,
    start_date: str | None = None,
    end_date: str | None = None,
) -> BacktestResult:
    """Backtest a desired close signal, executed from the following session.

    Costs are applied to every entry and exit as basis points of portfolio value.
    Optional date bounds are inclusive. Signals and returns are first calculated on the
    complete input history, so rows before start_date warm up indicators and provide
    the prior-session signal. The report and equity curve then start at start_date.
    Returns assume fractional allocation and no leverage, tax, or slippage beyond
    the configured cost. These simplifying assumptions are educational, not live-ready.
    """
    if initial_capital <= 0:
        raise ValueError("initial_capital must be positive.")
    if transaction_cost_bps < 0:
        raise ValueError("transaction_cost_bps cannot be negative.")
    if frame.empty:
        raise ValueError("Cannot backtest an empty frame.")

    daily = frame.copy()
    daily["asset_return"] = daily["Close"].pct_change().fillna(0.0)
    desired = signal.reindex(daily.index).fillna(0.0).clip(0.0, 1.0)
    daily["signal"] = desired
    daily["position"] = desired.shift(1).fillna(0.0)

    if start_date is not None:
        daily = daily.loc[daily.index >= pd.Timestamp(start_date)]
    if end_date is not None:
        daily = daily.loc[daily.index <= pd.Timestamp(end_date)]
    if daily.empty:
        raise ValueError("The selected date window contains no data rows.")

    # Start the evaluation portfolio at the first selected session. If the previous
    # close's signal calls for a position, charge its entry cost on this first session.
    daily["turnover"] = daily["position"].diff().abs().fillna(daily["position"].abs())
    cost_rate = transaction_cost_bps / 10_000.0
    daily["gross_strategy_return"] = daily["position"] * daily["asset_return"]
    daily["transaction_cost"] = daily["turnover"] * cost_rate
    daily["strategy_return"] = daily["gross_strategy_return"] - daily["transaction_cost"]
    daily["gross_equity"] = initial_capital * (1.0 + daily["gross_strategy_return"]).cumprod()
    daily["equity"] = initial_capital * (1.0 + daily["strategy_return"]).cumprod()
    prior_equity = daily["equity"].shift(1).fillna(initial_capital)
    daily["transaction_cost_amount"] = prior_equity * daily["transaction_cost"]
    daily["benchmark_equity"] = initial_capital * (1.0 + daily["asset_return"]).cumprod()
    daily["drawdown"] = daily["equity"] / daily["equity"].cummax() - 1.0

    trades = _trade_log(daily)
    observations = len(daily)
    years = observations / TRADING_DAYS
    total_return = daily["equity"].iloc[-1] / initial_capital - 1.0
    gross_total_return = daily["gross_equity"].iloc[-1] / initial_capital - 1.0
    cagr = (daily["equity"].iloc[-1] / initial_capital) ** (1 / years) - 1.0
    daily_risk_free = (1.0 + annual_risk_free_rate) ** (1 / TRADING_DAYS) - 1.0
    excess = daily["strategy_return"] - daily_risk_free
    standard_deviation = excess.std(ddof=1)
    sharpe = np.sqrt(TRADING_DAYS) * excess.mean() / standard_deviation if standard_deviation > 0 else 0.0
    win_rate = float((trades["return"] > 0).mean()) if not trades.empty else 0.0

    metrics = BacktestMetrics(
        start_date=daily.index.min().date().isoformat(),
        end_date=daily.index.max().date().isoformat(),
        observations=observations,
        total_return=float(total_return),
        gross_total_return=float(gross_total_return),
        cagr=float(cagr),
        sharpe_ratio=float(sharpe),
        max_drawdown=float(daily["drawdown"].min()),
        win_rate=win_rate,
        number_of_trades=len(trades),
        transaction_costs_paid=float(daily["transaction_cost_amount"].sum()),
        benchmark_total_return=float(daily["benchmark_equity"].iloc[-1] / initial_capital - 1.0),
    )
    return BacktestResult(daily=daily, trades=trades, metrics=metrics)
