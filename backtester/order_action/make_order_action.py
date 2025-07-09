import numpy as np

from numba import njit # type: ignore
from backtester.commons.type_commons import TSide, TOrderType, ORDER_TYPE__MARKET, TOffset, OFFSET__BOTH
from backtester.commons import BUY_SIGNAL, SELL_SIGNAL, NO_SIGNAL
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


# ---------------------------------------------------------------------------
# Helper to generate a ready-to-use order array based on a trading signal.
# ---------------------------------------------------------------------------


def market_order_for_signal(
    signal: int,
    size: float = 1.0,
    price: float = 0.0,
    stop_loss: float = 0.0,
    take_profit: float = 0.0,
    order_type: TOrderType = ORDER_TYPE__MARKET,
    offset: TOffset = OFFSET__BOTH,
    user_id: int = 0,
):
    """Return an (N, 9) ndarray representing a single order for BUY/SELL signal.

    If *signal* is NO_SIGNAL, an empty array with correct ndim / dtype is
    returned so that caller can concatenate safely without extra checks.
    """
    if signal == BUY_SIGNAL or signal == SELL_SIGNAL:
        return np.array([
            make_order_action_tuple(
                relative_size=0.0,
                absolute_size=size,
                stop_loss=stop_loss,
                take_profit=take_profit,
                price=price,
                order_type=order_type,
                side=signal,  # BUY_SIGNAL or SELL_SIGNAL carries side value
                offset=offset,
                user_id=user_id,
            )
        ], dtype=np.float64)

    # If no actionable signal, return properly-shaped empty array
    return np.empty((0, 9), dtype=np.float64)
