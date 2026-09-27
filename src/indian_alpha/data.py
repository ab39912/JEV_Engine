"""Market-data download, CSV loading, validation, and deterministic demo data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def _normalise_ohlcv(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a clean, date-indexed OHLCV frame with a stable schema."""
    data = frame.copy()
    if isinstance(data.columns, pd.MultiIndex):
        # yfinance may return either (Price, Ticker) or (Ticker, Price).
        for level in range(data.columns.nlevels):
            values = set(map(str, data.columns.get_level_values(level)))
            if set(OHLCV_COLUMNS).issubset(values):
                data.columns = data.columns.get_level_values(level)
                break

    data.columns = [str(column).strip().title() for column in data.columns]
    if "Adj Close" in data.columns:
        data = data.drop(columns=["Adj Close"])

    missing = set(OHLCV_COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(f"OHLCV data is missing columns: {sorted(missing)}")

    data = data[OHLCV_COLUMNS].copy()
    data.index = pd.to_datetime(data.index, errors="coerce").tz_localize(None)
    data.index.name = "Date"
    for column in OHLCV_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.loc[~data.index.isna()].sort_index()
    data = data.loc[~data.index.duplicated(keep="last")]
    data = data.dropna(subset=["Open", "High", "Low", "Close"])
    if data.empty:
        raise ValueError("No valid OHLCV rows remain after cleaning.")
    if (data[["Open", "High", "Low", "Close"]] <= 0).any().any():
        raise ValueError("Price columns must contain positive values.")
    data["Volume"] = data["Volume"].fillna(0.0).clip(lower=0.0)
    return data


def download_yahoo(symbol: str, start: str, end: str) -> pd.DataFrame:
    """Download daily adjusted OHLCV data from Yahoo Finance via yfinance.

    Common symbols: ^NSEI (NIFTY 50), RELIANCE.NS, TCS.NS, INFY.NS.
    The end date is exclusive, matching yfinance semantics.
    """
    if not symbol.strip():
        raise ValueError("Symbol cannot be empty.")
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError("Install project dependencies before downloading data.") from exc

    frame = yf.download(
        symbol,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        actions=False,
        progress=False,
        threads=False,
    )
    if frame.empty:
        raise RuntimeError(
            f"No data returned for {symbol}. Check the symbol, dates, and internet connection."
        )
    return _normalise_ohlcv(frame)


def load_csv(path: str | Path) -> pd.DataFrame:
    """Load OHLCV data from a CSV containing Date, Open, High, Low, Close, Volume."""
    frame = pd.read_csv(path)
    date_column = next((column for column in frame.columns if column.lower() == "date"), None)
    if date_column is None:
        raise ValueError("CSV must contain a Date column.")
    frame = frame.set_index(date_column)
    return _normalise_ohlcv(frame)


def save_csv(frame: pd.DataFrame, path: str | Path) -> Path:
    """Save a frame to CSV, creating its parent directory if necessary."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination)
    return destination


def make_demo_data(periods: int = 800, seed: int = 42) -> pd.DataFrame:
    """Create plausible deterministic OHLCV data for tests and offline learning."""
    if periods < 30:
        raise ValueError("Demo data requires at least 30 periods.")
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2020-01-01", periods=periods, name="Date")
    daily_returns = rng.normal(0.00035, 0.011, periods)
    close = 12_000 * np.exp(np.cumsum(daily_returns))
    overnight = rng.normal(0, 0.0025, periods)
    open_price = close * np.exp(overnight)
    spread = rng.uniform(0.001, 0.012, periods)
    high = np.maximum(open_price, close) * (1 + spread)
    low = np.minimum(open_price, close) * (1 - spread)
    volume = rng.lognormal(mean=17.5, sigma=0.35, size=periods).round()
    return _normalise_ohlcv(
        pd.DataFrame(
            {"Open": open_price, "High": high, "Low": low, "Close": close, "Volume": volume},
            index=dates,
        )
    )

