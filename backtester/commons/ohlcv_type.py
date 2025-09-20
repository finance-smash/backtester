import numpy as np
import numpy.typing as npt

from typing import Annotated



TOhlcvKeys = {
    'open': 0,
    'high': 1,
    'low': 2,
    'close': 3,
    'volume': 4
}

OHLCV__OPEN = TOhlcvKeys['open']
OHLCV__HIGH = TOhlcvKeys['high']
OHLCV__LOW = TOhlcvKeys['low']
OHLCV__CLOSE = TOhlcvKeys['close']
OHLCV__VOLUME = TOhlcvKeys['volume']

TOhlcvTuple = tuple[
    float, # open
    float, # high
    float, # low
    float, # close
    float, # volume
]

TOhlcv = Annotated[npt.NDArray[np.float64], TOhlcvTuple]

TMultiOhlcv = npt.NDArray[TOhlcv] # all olhcvs are intended to be parrallel in time
# i.e if X is a TMultiOhlcv, X[0][0] is at the same time as X[1][0]. 
# If no candle is available, the candle is none or with a close at 0