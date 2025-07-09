import time
import numpy as np

from backtester.commons import get_ohlcv_data
from backtester.strategy import backtest_strategy, Strategy, TStrategyParams


def run_and_assert(
    strategy: Strategy,
    ohlcv_path: str,
    expected_equity: float,
    begin_equity: float = 10_000_000_000,
    params: np.ndarray | None = None,
    warm_up: bool = True,
    slice_: tuple[int, int] | None = (0, 1500),
    places: int = 2,
):
    """Utility to perform common backtest routine inside unit tests.

    Parameters
    ----------
    strategy : Strategy
        Trading strategy to back-test.
    ohlcv_path : str
        Path where CSV data are stored (delegated to `get_ohlcv_data`).
    expected_equity : float
        Equity value expected by the test after rounding.
    begin_equity : float, default 10_000_000_000
        Starting capital for the back-test.
    params : np.ndarray | None, default None
        Strategy parameters array.  If None, an empty ndarray is used.
    warm_up : bool, default True
        If True, call `backtest_strategy` once before timing to warm the JIT.
    slice_ : tuple[int,int] | None, default (0, 1500)
        Slice to apply on the OHLCV array for faster tests.
    places : int, default 2
        Rounding precision when comparing final equity.
    """
    if params is None:
        params = np.array([])

    ohlcv = get_ohlcv_data('crypto', 'BTC-USDT', '15min', ohlcv_path)
    if slice_ is not None:
        ohlcv = ohlcv[slice_[0]:slice_[1]]

    if warm_up:
        backtest_strategy(strategy, ohlcv, (begin_equity, 0, False), params)

    start = time.time()
    result_info = backtest_strategy(strategy, ohlcv, (begin_equity, 0, False), params)
    duration = time.time() - start

    final_equity = round(result_info[2], places)
    print(f"Time taken: {duration} seconds")
    print(f"Final equity: {final_equity}")

    assert final_equity == expected_equity, (
        f"Expected equity {expected_equity}, got {final_equity}")

    return final_equity