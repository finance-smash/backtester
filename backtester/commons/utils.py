from numba import njit # type: ignore

from .type_commons import TSide, BUY, SELL, NO_SIDE



@njit
def get_reverse_side(side: TSide):
    if side == BUY:
        return SELL
    elif side == SELL:
        return BUY
    else:
        return NO_SIDE
