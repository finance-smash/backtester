import numpy.typing as npt
import numpy as np

from typing import Annotated, Literal
from backtester.commons.type_commons import TBUY, TSell


TOrderKeys = {
    'size': 0,
    'stop_loss': 1,
    'take_profit': 2,
    'limit': 3,
    'stop': 4,
    'side': 5,
    'user_id': 6,
}

ORDER__SIZE = TOrderKeys['size']
ORDER__STOP_LOSS = TOrderKeys['stop_loss']
ORDER__TAKE_PROFIT = TOrderKeys['take_profit']
ORDER__LIMIT = TOrderKeys['limit']
ORDER__STOP = TOrderKeys['stop']
ORDER__SIDE = TOrderKeys['side']
ORDER__USER_ID = TOrderKeys['user_id']

TOrderTuple = tuple[
    float | None, # size
    float | None, # stop_loss
    float | None, # take_profit
    float | None, # limit
    float | None, # stop
    TBUY | TSell, # side
    int # user_id
]

TOrder = Annotated[npt.NDArray[np.float64], TOrderTuple]

TOrders = Annotated[
    npt.NDArray[np.float64],
    TOrderTuple,
    Literal["N"]
]