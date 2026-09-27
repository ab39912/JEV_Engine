import numpy as np
import pandas as pd

from indian_alpha.backtest import run_backtest
from indian_alpha.data import make_demo_data


def test_signal_is_shifted_and_costs_reduce_return():
    frame = make_demo_data(periods=60)
    signal = pd.Series(1.0, index=frame.index)
    free = run_backtest(frame, signal, transaction_cost_bps=0)
    costly = run_backtest(frame, signal, transaction_cost_bps=25)

    assert free.daily["position"].iloc[0] == 0
    assert free.daily["position"].iloc[1] == 1
    assert costly.metrics.total_return < free.metrics.total_return
    assert costly.metrics.transaction_costs_paid > 0


def test_flat_signal_has_zero_strategy_return():
    frame = make_demo_data(periods=60)
    signal = pd.Series(0.0, index=frame.index)
    result = run_backtest(frame, signal)
    assert np.isclose(result.metrics.total_return, 0.0)
    assert result.metrics.number_of_trades == 0


def test_completed_trade_and_win_rate_are_reported():
    frame = make_demo_data(periods=60)
    signal = pd.Series(0.0, index=frame.index)
    signal.iloc[5:15] = 1.0
    result = run_backtest(frame, signal, transaction_cost_bps=0)
    assert result.metrics.number_of_trades == 1
    assert 0 <= result.metrics.win_rate <= 1

