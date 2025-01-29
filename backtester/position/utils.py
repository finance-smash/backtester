from numba import jit # type: ignore

from backtester.commons import BUY, SELL, NO_SIDE, TSide

@jit
def get_position_side(position_size: float) -> TSide:
    if position_size > 0:
        return BUY
    elif position_size < 0:
        return SELL
    return NO_SIDE