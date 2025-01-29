from numba import jit # type: ignore
from backtester.commons.type_commons import TSide
from .order_action_type import TOrderActionTuple


@jit
def make_order_action_tuple(
    relative_size: float | None,
    absolute_size: float | None,
    stop_loss: float | None,
    take_profit: float | None,
    limit: float | None,
    side: TSide,
    user_id: int
) -> TOrderActionTuple:
    return (relative_size, absolute_size, stop_loss, take_profit, limit, side, user_id)