import numpy as np
import numpy.typing as npt

from typing import Callable, Annotated
from numba import jit # type: ignore

from backtester.commons import BUY, SELL, NO_SIDE, TOhlcv, OHLCV__OPEN, OHLCV__CLOSE, OHLCV__LOW, OHLCV__HIGH, TSide, OHLCV__VOLUME
from backtester.order import TOrders, ORDER__SHAPE, ORDER__SIDE, ORDER__SIZE, ORDER__LIMIT, TOrderTuple
from backtester.order_action import ORDER_ACTION__ABSOLUTE_SIZE, ORDER_ACTION__SIDE, ORDER_ACTION__LIMIT
from backtester.position import TPosition, POSITION__AVG_PRICE, POSITION__SIZE, get_position_side

from .strategy import Strategy, TStrategyParams, TOrderFn


TBacktestSetupTuple = tuple[
    float, # cash
]

TBacktestSetup = Annotated[npt.NDArray[np.float64], TBacktestSetupTuple]

@jit
def is_between_strict(a: float, b: float, c: float) -> bool:
    return a < b < c or a > b > c

@jit
def backtest_strategy_loop(
    indicators: np.ndarray,
    order_fn: TOrderFn,
    data: TOhlcv,
    setup: TBacktestSetup,
    params: TStrategyParams
) -> tuple[TPosition, int, float, np.ndarray]:
    data_len = len(data)
    nb_of_orders = 0
    (equity,) = setup
    position: TPosition = (0., 0., 0.)
    pending_limit_orders: TOrders = np.empty(ORDER__SHAPE, dtype=np.float64)

    all_pls = np.empty((0), dtype=np.float64)

    for i in range(data_len - 1):
        last_close_price = data[i, OHLCV__CLOSE]
        current_open_price = data[i + 1, OHLCV__OPEN]
        curr_pos_avg_price = position[POSITION__AVG_PRICE]
        curr_pos_size = position[POSITION__SIZE]

        pending_limit_orders_len = len(pending_limit_orders)
        order_actions = order_fn(indicators, i, params)

        if pending_limit_orders_len > 0:
            for pending_limit_orders_index in range(pending_limit_orders_len):
                limit_order = pending_limit_orders[pending_limit_orders_index]
                limit_order_side = limit_order[ORDER__SIDE]
                limit_order_size = limit_order[ORDER__SIZE]
                limit_order_price = limit_order[ORDER__LIMIT]

                last_low_price = data[i, OHLCV__LOW]
                last_high_price = data[i, OHLCV__HIGH]
                last_open_price = data[i, OHLCV__OPEN]
                last_last_close_price = data[i - 1, OHLCV__CLOSE] if i >= 1 else None
                is_price_between_last_close_and_open = (
                    last_last_close_price is not None and 
                    is_between_strict(
                        last_last_close_price,
                        limit_order_price,
                        last_open_price
                    )
                )
                if is_price_between_last_close_and_open:                        
                    limit_order_price = last_open_price

                if last_low_price < limit_order_price < last_high_price or is_price_between_last_close_and_open:
                    (equity, position, all_pls) = applicate_order(
                        side=limit_order_side,
                        size=limit_order_size,
                        price=limit_order_price,
                        current_position_size=curr_pos_size,
                        current_position_avg_price=curr_pos_avg_price,
                        last_close_price=last_close_price,
                        current_equity=equity,
                        all_pls=all_pls,
                    )
                    mask = np.ones(len(pending_limit_orders), dtype=np.bool_)
                    mask[pending_limit_orders_index] = False
                    pending_limit_orders = pending_limit_orders[mask]

        if len(order_actions) > 0:
            nb_of_orders += len(order_actions)

            for order_action in order_actions:
                absolute_size = order_action[ORDER_ACTION__ABSOLUTE_SIZE]
                side: TSide = order_action[ORDER_ACTION__SIDE]
                size: float = 0.0

                if absolute_size > 0:
                    size = absolute_size
                else:
                    print(f"Only absolute size is accepted for now")

                limit = order_action[ORDER_ACTION__LIMIT]

                if limit > 0:
                    limit_order_tuple: TOrderTuple = (
                        size,
                        0.0, # no stop loss for now
                        0.0, # no take profit for now
                        limit,
                        0.0, # a limit order is not a stop order
                        side,
                        0, # no user id for now
                    )
                    if side == BUY and limit >= last_close_price:
                        print(f"Cannot place a buy limit order at {str(limit)} because the last close price is {str(last_close_price)}")
                        continue
                    elif side == SELL and limit <= last_close_price:
                        print(f"Cannot place a sell limit order at {str(limit)} because the last close price is {str(last_close_price)}")
                        continue
                    
                    pending_limit_orders = np.append(
                        pending_limit_orders,
                        np.array([limit_order_tuple], dtype=np.float64),
                        axis=0
                    )
                else:
                    (equity, position, all_pls) = applicate_order(
                        side=side,
                        size=size,
                        price=current_open_price,
                        current_position_size=curr_pos_size,
                        current_position_avg_price=curr_pos_avg_price,
                        last_close_price=last_close_price,
                        current_equity=equity,
                        all_pls=all_pls,
                    )

        next_pos_size = position[POSITION__SIZE]
        if next_pos_size > 0:
            next_pos_avg_price = position[POSITION__AVG_PRICE]
            next_position_pl = (current_open_price - next_pos_avg_price) * next_pos_size
            position = (next_pos_size, next_pos_avg_price, next_position_pl)
        
    return (position, nb_of_orders, equity, all_pls)


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

@jit
def applicate_order(
    side: TSide,
    size: float,
    price: float,
    current_position_size: float,
    current_position_avg_price: float,
    last_close_price: float,
    current_equity: float,
    all_pls: np.ndarray,
):
    equity = current_equity
    current_position_side = get_position_side(current_position_size)

    side_sign = -1 if side == SELL else 1 if side == BUY else 0
    price_to_pay = size * price
    next_pos_size = current_position_size + side_sign * size
    next_pos_side = get_position_side(next_pos_size)
    next_pos_avg_price = current_position_avg_price
    position_changed_side = current_position_side != next_pos_side
    order_same_side = side == current_position_side
    
    if next_pos_size == 0:
        final_pos_pl = (price - current_position_avg_price) * current_position_size
        equity += final_pos_pl
        all_pls = np.append(all_pls, final_pos_pl)
        position = (0., 0., 0.)
    else:
        if position_changed_side:

            if current_position_side != NO_SIDE and next_pos_side != NO_SIDE:
                size_to_close = np.abs(next_pos_size - current_position_size)
                to_close_pl_with_next_open = (price - current_position_avg_price) * size_to_close
                equity += to_close_pl_with_next_open
                all_pls = np.append(all_pls, to_close_pl_with_next_open)
            
            next_pos_avg_price = price
        elif order_same_side:
            next_pos_avg_price = (
                current_position_avg_price * current_position_size + price_to_pay
            ) / next_pos_size
        else:
            reduced_size = np.abs(next_pos_size - current_position_size)
            reduced_size_pl = (price - current_position_avg_price) * reduced_size
            equity += reduced_size_pl
            all_pls = np.append(all_pls, reduced_size_pl)
        next_pos_pl = (last_close_price - next_pos_avg_price) * next_pos_size
        position = (next_pos_size, next_pos_avg_price, next_pos_pl)

    return (equity, position, all_pls)