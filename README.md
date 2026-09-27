# Indian Alpha Research Engine — Phase 1

An educational, reproducible starting point for researching daily NIFTY 50 and Indian
equity strategies. It downloads historical data, calculates transparent technical
features, produces a deliberately simple long-only signal, and backtests that signal
with next-session execution and configurable transaction costs.

> **Research only.** This project has no broker connection, order placement, API keys,
> live execution, or real-money functionality. Yahoo Finance data is convenient for
> learning but is not an exchange-certified market-data feed.

## What is included

```text
indian-alpha-phase1/
├── data/
│   ├── raw/                 # downloaded/local OHLCV files (ignored by Git)
│   └── results/             # metrics, equity curve, and trade log
├── src/indian_alpha/
│   ├── data.py              # Yahoo download, CSV validation, demo data
│   ├── features.py          # returns, SMA/EMA, RSI, volatility, volume
│   ├── strategy.py          # explainable trend + RSI rule
│   ├── backtest.py          # execution, costs, trades, performance metrics
│   ├── reporting.py         # console and CSV/JSON outputs
│   └── cli.py               # command-line interface
├── tests/                   # focused correctness checks
├── pyproject.toml           # package and tool configuration
└── requirements.txt         # convenient development installation
```

## Windows and VS Code setup

### 1. Install prerequisites

- Install Python 3.10 or newer from python.org. During installation, select
  **Add Python to PATH**.
- Install Visual Studio Code and its **Python** extension.
- Open this project folder in VS Code: **File → Open Folder**.

### 2. Create an isolated environment

Open the VS Code terminal (**Terminal → New Terminal**) and run:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation for this terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Then choose the environment in VS Code: press `Ctrl+Shift+P`, run
**Python: Select Interpreter**, and select `.venv`.

## First run: offline end-to-end demo

This does not use the internet. It creates deterministic synthetic OHLCV data and runs
the same feature, strategy, backtest, and reporting path used for real historical data.

```powershell
indian-alpha backtest --demo
```

The terminal prints performance metrics. Detailed output appears in
`data/results/latest/`:

- `metrics.json`: machine-readable summary;
- `equity_curve.csv`: daily features, positions, returns, costs, equity, and drawdown;
- `trades.csv`: completed entry/exit pairs and their returns.

## Download historical Indian market data

Yahoo Finance symbols commonly used for this learning project are:

- `^NSEI` — NIFTY 50 index;
- `RELIANCE.NS` — Reliance Industries on NSE;
- `TCS.NS` — Tata Consultancy Services on NSE;
- `INFY.NS` — Infosys on NSE.

Download NIFTY 50 daily data (the end date is exclusive):

```powershell
indian-alpha download --symbol "^NSEI" --start 2015-01-01 --end 2025-01-01 --output data/raw/nifty50.csv
```

Run the backtest:

```powershell
indian-alpha backtest --csv data/raw/nifty50.csv --cost-bps 10 --risk-free-rate 0.06
```

### Evaluate a later date window

Use `--start-date` and `--end-date` to report a selected period while retaining earlier
rows in the CSV for SMA/RSI warm-up. Both bounds are inclusive. For example, download
history through September 2026, then evaluate only 2025 onward:

```powershell
indian-alpha download --symbol "^NSEI" --start 2015-01-01 --end 2026-09-28 --output data/raw/nifty50.csv
indian-alpha backtest --csv data/raw/nifty50.csv --start-date 2025-01-01 --end-date 2026-09-27 --cost-bps 10 --output-dir data/results/holdout-2025-onward
```

Earlier rows calculate features and the prior-session signal, but the reported equity
curve, returns, and benchmark comparison begin at the first selected session. At that
boundary, the backtest starts with the previous session's signal and charges an entry
cost if it begins invested. Keep strategy settings and costs fixed before evaluating a
holdout. Since the 2015–2024 results have already been inspected in this learning run,
2025 onward is a more useful next check than re-splitting those same years, although
continuing to change rules after seeing holdout results will also make that period
exploratory.

For an NSE equity, change both the symbol and file name:

```powershell
indian-alpha download --symbol "RELIANCE.NS" --start 2015-01-01 --end 2025-01-01 --output data/raw/reliance.csv
indian-alpha backtest --csv data/raw/reliance.csv --output-dir data/results/reliance
```

Downloaded prices use `auto_adjust=True`, so the OHLC values are adjusted for corporate
actions where Yahoo supplies the required information. Always inspect suspicious gaps
and compare important research data with an authoritative source.

## The features

`features.py` adds:

- simple one-day return and log return;
- fast and slow simple moving averages (SMA);
- fast and slow exponential moving averages (EMA);
- 14-session Wilder-style Relative Strength Index (RSI);
- rolling daily-return standard deviation annualised with `sqrt(252)`;
- rolling average volume and current-volume ratio;
- close × volume as a rough traded-value/liquidity measure.

Warm-up rows naturally contain missing values. The strategy remains flat until all
features it needs are available.

## The example strategy

The rule is intentionally plain enough to audit:

```text
desired long position = 1 when
    fast SMA > slow SMA
    AND RSI is between 50 and 70
otherwise = 0
```

The signal is calculated from the current close, then shifted one trading session before
it becomes a position. This prevents the common mistake of using a closing price to make
an impossible trade at that same close. You can change the defaults:

```powershell
indian-alpha backtest --csv data/raw/nifty50.csv --fast 50 --slow 200 --rsi-floor 45 --rsi-ceiling 75
```

This is an example hypothesis, not an assertion that these parameters have predictive
power. Repeatedly tuning them on the same history creates overfitting.

## Backtest assumptions and metrics

The backtester is daily, long-only, unlevered, and allows fractional portfolio exposure.
It applies the specified one-way transaction cost on every position change. For example,
10 basis points costs 0.10% on entry and another 0.10% on exit.

It reports:

- **net total return** after modeled costs;
- **gross total return** before modeled costs;
- **CAGR** using 252 observations per trading year;
- **Sharpe ratio** from annualised daily excess returns;
- **maximum drawdown** from the net equity curve;
- **win rate** across completed round-trip trades;
- **number of trades** as completed round trips;
- **estimated transaction costs paid** in portfolio currency;
- **buy-and-hold return** over the same rows.

An open position on the final date is visible in `equity_curve.csv` but is not counted as
a completed trade in the trade log or win rate.

## Use your own CSV

The required schema is:

```csv
Date,Open,High,Low,Close,Volume
2024-01-01,100,103,99,102,1500000
```

Dates are sorted, duplicates keep their final occurrence, invalid price rows are removed,
and non-positive prices are rejected. Volume may be zero; this matters for indices such as
NIFTY 50, where a meaningful traded volume may not be published.

## Run the tests

```powershell
python -m pytest
```

Optional style check:

```powershell
python -m ruff check .
```

## Important limitations before Phase 2

- Yahoo data availability and corrections are outside this project's control.
- The model does not include taxes, bid/ask spread, market impact, partial fills, or
  instrument-specific charges beyond the single cost assumption.
- Index levels themselves are not directly tradable; an ETF or futures contract has
  different prices, costs, tracking error, expiry, and liquidity.
- Results do not include walk-forward validation, parameter stability tests, survivorship
  bias controls for a changing NIFTY membership, or out-of-sample evaluation.
- No result here is investment advice or evidence of future performance.

Those limitations are the natural boundary for Phase 1. A later phase can add a proper
experiment registry, walk-forward splits, multiple instruments, portfolio construction,
and more realistic execution—still in paper/research mode before any live integration.
