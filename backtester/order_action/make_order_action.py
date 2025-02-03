import numpy as np

from numba import njit # type: ignore
from backtester.commons.type_commons import TSide, TOrderType, ORDER_TYPE__MARKET, TOffset, OFFSET__BOTH
from .order_action_type import TOrderActionTuple, TOrderAction



@njit
def make_order_action_tuple(
    relative_size: float = 0.0,
    absolute_size: float = 0.0,
    stop_loss: float = 0.0,
    take_profit: float = 0.0,
    price: float = 0.0,
    order_type: TOrderType = ORDER_TYPE__MARKET,
    side: TSide = 0,
    offset: TOffset = OFFSET__BOTH,
    user_id: int = 0,
) -> TOrderActionTuple:
    return (
        relative_size,
        absolute_size,
        stop_loss,
        take_profit,
        price,
        order_type,
        side,
        offset,
        user_id,
    )


@njit
def make_order_action(
    relative_size: float = 0.0,
    absolute_size: float = 0.0,
    stop_loss: float = 0.0,
    take_profit: float = 0.0,
    price: float = 0.0,
    order_type: TOrderType = ORDER_TYPE__MARKET,
    side: TSide = 0,
    offset: TOffset = OFFSET__BOTH,
    user_id: int = 0,
) -> TOrderAction:
    return np.array(make_order_action_tuple(
        relative_size=relative_size,
        absolute_size=absolute_size,
        stop_loss=stop_loss,
        take_profit=take_profit,
        price=price,
        order_type=order_type,
        side=side,
        offset=offset,
        user_id=user_id,
    ), dtype=np.float64)
