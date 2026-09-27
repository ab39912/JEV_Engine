"""Command-line entry point for data collection and research runs."""

from __future__ import annotations

import argparse
from pathlib import Path

from indian_alpha.backtest import run_backtest
from indian_alpha.data import download_yahoo, load_csv, make_demo_data, save_csv
from indian_alpha.features import add_features
from indian_alpha.reporting import format_report, save_results
from indian_alpha.strategy import trend_rsi_signal


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Educational Indian equity research engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download", help="Download daily Yahoo Finance OHLCV")
    download.add_argument("--symbol", default="^NSEI", help="^NSEI or an NSE symbol such as RELIANCE.NS")
    download.add_argument("--start", default="2015-01-01")
    download.add_argument("--end", default="2025-01-01", help="Exclusive end date")
    download.add_argument("--output", type=Path, default=Path("data/raw/nifty50.csv"))

    backtest = subparsers.add_parser("backtest", help="Run a CSV or deterministic demo backtest")
    source = backtest.add_mutually_exclusive_group(required=True)
    source.add_argument("--csv", type=Path, help="CSV containing Date and OHLCV columns")
    source.add_argument("--demo", action="store_true", help="Use offline synthetic data")
    backtest.add_argument("--fast", type=int, default=20)
    backtest.add_argument("--slow", type=int, default=50)
    backtest.add_argument("--rsi-window", type=int, default=14)
    backtest.add_argument("--rsi-floor", type=float, default=50.0)
    backtest.add_argument("--rsi-ceiling", type=float, default=70.0)
    backtest.add_argument("--capital", type=float, default=100_000.0)
    backtest.add_argument("--cost-bps", type=float, default=10.0)
    backtest.add_argument("--risk-free-rate", type=float, default=0.0, help="Annual decimal rate, e.g. 0.06")
    backtest.add_argument(
        "--start-date",
        help="Inclusive first date to report; earlier CSV rows warm up indicators",
    )
    backtest.add_argument(
        "--end-date",
        help="Inclusive last date to report; later CSV rows are ignored in the report",
    )
    backtest.add_argument("--output-dir", type=Path, default=Path("data/results/latest"))
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "download":
        frame = download_yahoo(args.symbol, args.start, args.end)
        destination = save_csv(frame, args.output)
        print(f"Saved {len(frame):,} rows for {args.symbol} to {destination}")
        return

    frame = make_demo_data() if args.demo else load_csv(args.csv)
    featured = add_features(
        frame,
        fast_window=args.fast,
        slow_window=args.slow,
        rsi_window=args.rsi_window,
    )
    signal = trend_rsi_signal(
        featured,
        fast_window=args.fast,
        slow_window=args.slow,
        rsi_window=args.rsi_window,
        rsi_entry_floor=args.rsi_floor,
        rsi_entry_ceiling=args.rsi_ceiling,
    )
    result = run_backtest(
        featured,
        signal,
        initial_capital=args.capital,
        transaction_cost_bps=args.cost_bps,
        annual_risk_free_rate=args.risk_free_rate,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    destination = save_results(result, args.output_dir)
    print(format_report(result))
    print(f"\nSaved detailed results to {destination}")


if __name__ == "__main__":
    main()

