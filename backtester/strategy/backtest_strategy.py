import numpy as np
import numpy.typing as npt

from typing import Callable, Annotated
from numba import jit # type: ignore

from backtester.commons import BUY, SELL, TOhlcv, OHLCV__OPEN, OHLCV__CLOSE
from backtester.order_action import ORDER_ACTION__ABSOLUTE_SIZE, ORDER_ACTION__SIDE, ORDER_ACTION__LIMIT
from backtester.position import TPosition, POSITION__AVG_PRICE, POSITION__SIZE

from .strategy import Strategy, TStrategyParams, TOrderFn


TBacktestSetupTuple = tuple[
    float, # cash
]

TBacktestSetup = Annotated[npt.NDArray[np.float64], TBacktestSetupTuple]

@jit
def backtest_strategy_loop(
    indicators: np.ndarray,
    order_fn: TOrderFn,
    data: TOhlcv,
    setup: TBacktestSetup,
    params: TStrategyParams
) -> tuple[TPosition, int, float, float, np.ndarray]:
    data_len = len(data)
    nb_of_orders = 0
    equity = setup[0]
    position: TPosition = (0., 0., 0.)
    current_open_price = 0.

    current_pos_size = 0.
    last_pos_size = 0.
    last_pos_pl = 0.
    current_pos_pl = 0.

    all_pls = np.empty((0), dtype=np.float64)

    for i in range(data_len):
        if i < 49:
            continue

        current_close_price = data[i, OHLCV__CLOSE]
        curr_pos_avg_price = position[POSITION__AVG_PRICE]
        last_pos_size = current_pos_size
        current_pos_size = position[POSITION__SIZE]
        curr_pos_size = current_pos_size
        last_pos_pl = current_pos_pl
        curr_pos_pl = (current_close_price - curr_pos_avg_price) * curr_pos_size
        current_pos_pl = curr_pos_pl
        curr_pos_side = BUY if curr_pos_size > 0 else SELL

        if i < data_len - 1:
            order_actions = order_fn(indicators, i, params)
            current_open_price = data[i + 1, OHLCV__OPEN]

            if len(order_actions) > 0:
                nb_of_orders += len(order_actions)
                for order_action in order_actions:
                    absolute_size = order_action[ORDER_ACTION__ABSOLUTE_SIZE]
                    side = order_action[ORDER_ACTION__SIDE]
                    size: float = 0.0

                    if absolute_size > 0:
                        size = absolute_size
                    else:
                        print(f"Only absolute size is accepted for now")

                    limit = order_action[ORDER_ACTION__LIMIT]

                    if limit > 0:
                        print(f"Limit is not supported for now")
                    else:
                        side_sign = -1 if side == SELL else 1 if side == BUY else 0
                        price_to_pay = size * current_open_price
                        next_pos_size = curr_pos_size + side_sign * size
                        if next_pos_size == 0:
                            final_pos_pl_with_next_open = (current_open_price - curr_pos_avg_price) * curr_pos_size
                            equity += final_pos_pl_with_next_open
                            all_pls = np.append(all_pls, final_pos_pl_with_next_open)
                            position = (0., 0., 0.)
                        else:
                            next_pos_side = BUY if next_pos_size > 0 else SELL
                            next_pos_avg_price = curr_pos_avg_price
                            if curr_pos_side == next_pos_side:
                                if side == curr_pos_side:
                                    next_pos_avg_price = (
                                        curr_pos_avg_price * curr_pos_size + price_to_pay
                                    ) / next_pos_size
                                else:
                                    next_pos_avg_price = curr_pos_avg_price
                            else:
                                next_pos_avg_price = current_open_price

                            next_pos_pl = (current_close_price - next_pos_avg_price) * next_pos_size

                            position = (next_pos_size, next_pos_avg_price, next_pos_pl)  
            else:
                next_position_pl = (current_close_price - curr_pos_avg_price) * curr_pos_size
                position = (curr_pos_size, curr_pos_avg_price, next_position_pl)
        else:
            next_position_pl = (current_close_price - curr_pos_avg_price) * curr_pos_size
            position = (curr_pos_size, curr_pos_avg_price, next_position_pl)
    
    return (position, nb_of_orders, equity, current_open_price, all_pls)

def backtest_strategy_inner(
        indicators_fn: Callable,
        order_fn: Callable,
        data: TOhlcv,
        setup: TBacktestSetup,
        params: TStrategyParams
    ):
    indicators = indicators_fn(data, params)
    return backtest_strategy_loop(indicators, order_fn, data, setup, params)


def backtest_strategy(strategy: Strategy, data: TOhlcv, setup: TBacktestSetup, params: TStrategyParams) -> np.ndarray:
    return backtest_strategy_inner(
        strategy.indicators_fn,
        strategy.order_fn,
        data,
        setup,
        params
    )