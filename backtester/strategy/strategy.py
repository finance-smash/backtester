import numpy as np
import numpy.typing as npt

from typing import Callable, Annotated
from numba import njit # type: ignore

from backtester.order import TOrders
from backtester.order_action import TOrderActions
from backtester.commons import TOhlcv



TStrategyParams = npt.NDArray[np.float64]

TIndicatorsFn = Callable[[TOhlcv, TStrategyParams], np.ndarray]

TOrderFn = Callable[[np.ndarray, int, TStrategyParams, TOrders], TOrderActions]

TBacktestSetup = tuple[
    float, # cash
]

TBacktestSetupArr = Annotated[npt.NDArray[np.float64], TBacktestSetup]



class Strategy:
    def __init__(
        self,
        default_params: TStrategyParams,
        indicators_fn: TIndicatorsFn,
        order_fn: TOrderFn,
    ):
        self.default_params = default_params
        self.indicators_fn = indicators_fn
        self.order_fn = njit(order_fn)