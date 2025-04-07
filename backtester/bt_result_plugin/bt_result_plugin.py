import numpy as np
from typing import Callable

from backtester.strategy.backtest_strategy import TBacktestResult

TBtResultPlugin = Callable[[TBacktestResult], np.ndarray]
