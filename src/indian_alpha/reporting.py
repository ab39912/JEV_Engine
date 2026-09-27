"""Console and file reporting helpers."""

from __future__ import annotations

import json
from pathlib import Path

from indian_alpha.backtest import BacktestResult


def format_report(result: BacktestResult) -> str:
    metrics = result.metrics
    rows = [
        ("Period", f"{metrics.start_date} to {metrics.end_date}"),
        ("Observations", f"{metrics.observations:,}"),
        ("Net total return", f"{metrics.total_return:.2%}"),
        ("Gross total return", f"{metrics.gross_total_return:.2%}"),
        ("CAGR", f"{metrics.cagr:.2%}"),
        ("Sharpe ratio", f"{metrics.sharpe_ratio:.2f}"),
        ("Max drawdown", f"{metrics.max_drawdown:.2%}"),
        ("Completed trades", f"{metrics.number_of_trades}"),
        ("Trade win rate", f"{metrics.win_rate:.2%}"),
        ("Estimated costs paid", f"INR {metrics.transaction_costs_paid:,.2f}"),
        ("Buy-and-hold return", f"{metrics.benchmark_total_return:.2%}"),
    ]
    width = max(len(label) for label, _ in rows)
    return "\n".join(f"{label:<{width}} : {value}" for label, value in rows)


def save_results(result: BacktestResult, output_dir: str | Path) -> Path:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    result.daily.to_csv(destination / "equity_curve.csv")
    result.trades.to_csv(destination / "trades.csv", index=False)
    with (destination / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(result.metrics.to_dict(), handle, indent=2)
    return destination

