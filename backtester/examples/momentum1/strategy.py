import numpy as np

from backtester.commons.ohlcv_type import TOhlcv
from backtester.commons.type_commons import TOhlcvDataDomain, TOhlcvDataPathTuple, TOhlcvDataTimeframe
from backtester.strategy.strategy import TStrategyParams

DEFAULT_VOLUME_LOOKBACK = 10
DEFAULT_TAKE_BEST_X_BY_VOLUME = 20
DEFAULT_RATE_OF_CHANGE_LOOKBACK = 10

def make_indicators_fn(
    ohlcv_data_path_tuples: tuple[TOhlcvDataDomain, TOhlcvDataTimeframe] | list[TOhlcvDataPathTuple],
    volume_lookback = DEFAULT_VOLUME_LOOKBACK,
    take_best_x_by_volume = DEFAULT_TAKE_BEST_X_BY_VOLUME,
    rate_of_change_lookback = DEFAULT_RATE_OF_CHANGE_LOOKBACK,
):
    if isinstance(ohlcv_data_path_tuples, tuple):
        raise ValueError("ohlcv_data_path_tuples must be a list, tuple is not supported for now")

    

    def indicators_fn(data: TOhlcv, params: TStrategyParams) -> np.ndarray:
        return np.array([])

    return indicators_fn