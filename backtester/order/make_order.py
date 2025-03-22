from typing import Literal
from numba import njit # type: ignore
from backtester.commons.type_commons import OFFSET__BOTH, TOffset, TSide, TOrderType, ORDER_TYPE__MARKET
from .order_type import TOrderTuple



@njit
def make_order_tuple(
    size: float = 0.0,
    stop_loss: float = 0.0,
    take_profit: float = 0.0,
    price: float = 0.0,
    order_type: TOrderType = ORDER_TYPE__MARKET,
    side: TSide = 0,
    offset: TOffset = OFFSET__BOTH,
    candle_index: int = 0,
    user_id: int = 0,
) -> TOrderTuple:
    return (
        size,
        stop_loss,
        take_profit,
        price,
        order_type,
        side,
        offset,
        candle_index,
        user_id,
    )