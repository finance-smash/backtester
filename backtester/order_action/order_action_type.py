import numpy.typing as npt
import numpy as np

from typing import Annotated, Literal
from backtester.commons.type_commons import TSide


TOrderActionKeys = {
    "relative_size": 0,
    "absolute_size": 1,
    "stop_loss": 2,
    "take_profit": 3,
    "limit": 4,
    "side": 5,
    "user_id": 6
}

ORDER_ACTION__RELATIVE_SIZE = TOrderActionKeys['relative_size']
ORDER_ACTION__ABSOLUTE_SIZE = TOrderActionKeys['absolute_size']
ORDER_ACTION__STOP_LOSS = TOrderActionKeys['stop_loss']
ORDER_ACTION__TAKE_PROFIT = TOrderActionKeys['take_profit']
ORDER_ACTION__LIMIT = TOrderActionKeys['limit']
ORDER_ACTION__SIDE = TOrderActionKeys['side']
ORDER_ACTION__USER_ID = TOrderActionKeys['user_id']

TOrderActionTuple = tuple[
    float | None, # relative_size
    float | None, # absolute_size
    float | None, # stop_loss
    float | None, # take_profit
    float | None, # limit
    TSide, # side
    int # user_id
]

TOrderAction = Annotated[npt.NDArray[np.float64], TOrderActionTuple]

TOrderActions = Annotated[
    npt.NDArray[np.float64],
    TOrderActionTuple,
    Literal["N"]
]
