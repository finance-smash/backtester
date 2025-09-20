import numpy as np
import numpy.typing as npt

from typing import Callable, Annotated
from numba import njit # type: ignore

from backtester.order import TOrders
from backtester.order_action import TOrderActions
from backtester.commons import TMultiOhlcv

from backtester.position import TPositionTripleArray



TStrategyParams = npt.NDArray[np.float64]

TIndicatorsFn = Callable[[TMultiOhlcv, TStrategyParams], np.ndarray]

TOrderFn = Callable[[
    np.ndarray, # indicators for each ohlcv [ohlcv1 : [ind1, ind2, ...], ohlcv2 : [ind1, ind2, ...], ...]
    int, # index
    TStrategyParams, # params
    npt.NDArray[TOrders], # pending_orders
    npt.NDArray[TPositionTripleArray], # position_triple
    np.ndarray, # state
], tuple[npt.NDArray[TOrderActions], np.ndarray]]

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