import numpy.typing as npt
import numpy as np

from typing import Annotated, Literal
from backtester.commons.type_commons import TSide, TOffset, TOrderType



TOrderActionKeys = {
    "relative_size": 0,
    "absolute_size": 1,
    "stop_loss": 2,
    "take_profit": 3,
    "price": 4,
    "order_type": 5,
    "side": 6,
    "offset": 7,
    "user_id": 8
}

ORDER_ACTION__RELATIVE_SIZE = TOrderActionKeys['relative_size']
ORDER_ACTION__ABSOLUTE_SIZE = TOrderActionKeys['absolute_size']
ORDER_ACTION__STOP_LOSS = TOrderActionKeys['stop_loss']
ORDER_ACTION__TAKE_PROFIT = TOrderActionKeys['take_profit']
ORDER_ACTION__PRICE = TOrderActionKeys['price']
ORDER_ACTION__ORDER_TYPE = TOrderActionKeys['order_type']
ORDER_ACTION__SIDE = TOrderActionKeys['side']
ORDER_ACTION__OFFSET = TOrderActionKeys['offset']
ORDER_ACTION__USER_ID = TOrderActionKeys['user_id']

TOrderActionTuple = tuple[
    float, # relative_size
    float, # absolute_size
    float, # stop_loss
    float, # take_profit
    float, # price
    TOrderType, # order_type
    TSide, # side
    TOffset, # offset
    int # user_id
]

TOrderAction = Annotated[npt.NDArray[np.float64], TOrderActionTuple]

TOrderActions = Annotated[
    npt.NDArray[np.float64],
    TOrderActionTuple,
    Literal["N"]
]

ORDER_ACTION__SHAPE = (len(TOrderActionKeys),)