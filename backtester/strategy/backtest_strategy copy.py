import numpy as np
import numpy.typing as npt

from typing import Callable, Annotated, Literal
from numba import njit # type: ignore

from backtester.commons import BUY, SELL, NO_SIDE, TOhlcv, OHLCV__OPEN, OHLCV__CLOSE, OHLCV__LOW, OHLCV__HIGH, TSide, get_reverse_side, \
    MAX_NUMBER_OF_PENDING_ORDERS, MAX_NUMBER_OF_OCO_ORDERS, ORDER_TYPE__LIMIT, ORDER_TYPE__MARKET, ORDER_TYPE__STOP
from backtester.order import TOrders, ORDER__SHAPE, ORDER__SIDE, ORDER__SIZE, ORDER__PRICE, ORDER__ORDER_TYPE, TOrderTuple, make_order_tuple, TOrderKeys
from backtester.order_action import ORDER_ACTION__ABSOLUTE_SIZE, ORDER_ACTION__SIDE, ORDER_ACTION__PRICE, ORDER_ACTION__ORDER_TYPE, \
    ORDER_ACTION__STOP_LOSS, ORDER_ACTION__TAKE_PROFIT, TOrderAction, make_order_action
from backtester.position import TPosition, POSITION__AVG_PRICE, POSITION__SIZE, get_position_side

from .strategy import Strategy, TStrategyParams, TOrderFn



TPendingOrderWithOco = Annotated[
    npt.NDArray[np.float64],
    TOrderTuple,
    MAX_NUMBER_OF_OCO_ORDERS,
]


TPendingOrderWithOcos = Annotated[
    TPendingOrderWithOco,
    Literal["N"]
]


TBacktestSetupTuple = tuple[
    float, # cash
]


TBacktestSetup = Annotated[npt.NDArray[np.float64], TBacktestSetupTuple]



@njit
def get_pending_order_ocos(pending_order_with_oco: TPendingOrderWithOco):
    return pending_order_with_oco[len(TOrderKeys):]


@njit
def get_next_pending_order_free_indice(pending_orders: TPendingOrderWithOcos):
    next_nan_indice = np.argmax(np.isnan(pending_orders[:,0]))
    if next_nan_indice == 0 and not np.isnan(pending_orders[0, ORDER__SIZE]):
        raise ValueError(f"MAX_NUMBER_OF_PENDING_ORDERS is too low. Please increase it. Current value: {MAX_NUMBER_OF_PENDING_ORDERS}")
    return int(next_nan_indice)


@njit
def is_between_strict(lim1: float, x: float, lim2: float) -> bool:
    return lim1 < x < lim2 or lim1 > x > lim2



@njit
def is_between_inclusive(lim1: float, x: float, lim2: float) -> bool:
    return lim1 <= x <= lim2 or lim1 >= x >= lim2



@njit
def is_between(lim1: float, x: float, lim2: float, strict: bool = True) -> bool:
    if strict:
        return is_between_strict(lim1, x, lim2)
    else:
        return is_between_inclusive(lim1, x, lim2)



@njit
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
    pending_orders: TPendingOrderWithOcos = np.empty(
        (MAX_NUMBER_OF_PENDING_ORDERS, ORDER__SHAPE[1] + MAX_NUMBER_OF_OCO_ORDERS),
        dtype=np.float64
    )
    pending_orders.fill(np.nan)
    all_pls = np.empty((0), dtype=np.float64)


    for i in range(data_len - 1):
        (
            equity,
            position,
            all_pls,
            pending_orders
        ) = applicate_all_pending_orders(
            pending_orders=pending_orders,
            current_equity=equity,
            current_position=position,
            current_all_pls=all_pls,
            data=data,
            i=i
        )

        current_close_price = data[i, OHLCV__CLOSE]
        incoming_open_price = data[i + 1, OHLCV__OPEN]

        current_position_avg_price = position[POSITION__AVG_PRICE]
        current_position_size = position[POSITION__SIZE]

        order_actions = order_fn(indicators, i, params, pending_orders)
        order_actions_len = len(order_actions)


        if order_actions_len > 0:
            nb_of_orders += order_actions_len


            for order_action_index in range(order_actions_len):
                order_action: TOrderAction = order_actions[order_action_index]
                absolute_size = order_action[ORDER_ACTION__ABSOLUTE_SIZE]
                side: TSide = order_action[ORDER_ACTION__SIDE]
                reverse_side: TSide = get_reverse_side(side)
                size: float = 0.0


                if absolute_size > 0:
                    size = absolute_size
                else:
                    raise ValueError("Only absolute size is accepted for now")
                
                
                order_action[ORDER_ACTION__ABSOLUTE_SIZE] = size
                order_action_price = order_action[ORDER_ACTION__PRICE]
                order_action_order_type = order_action[ORDER_ACTION__ORDER_TYPE]


                if order_action_order_type == ORDER_TYPE__LIMIT:
                    if side == BUY and order_action_price >= current_close_price:
                        raise ValueError(f"Cannot place a buy limit order at {str(order_action_price)} because the last close price is {str(current_close_price)}")
                    elif side == SELL and order_action_price <= current_close_price:
                        raise ValueError(f"Cannot place a sell limit order at {str(order_action_price)} because the last close price is {str(current_close_price)}")
                    
                    (pending_orders, limit_order_indice) = register_pending_order(
                        order_action=make_order_action(
                            absolute_size=size,
                            price=order_action_price,
                            order_type=ORDER_TYPE__LIMIT,
                            side=side,
                            stop_loss=order_action[ORDER_ACTION__STOP_LOSS],
                            take_profit=order_action[ORDER_ACTION__TAKE_PROFIT],
                        ),
                        pending_orders=pending_orders,
                    )

                    if np.isnan(limit_order_indice):
                        raise ValueError("Failed to register limit order - received NaN index")

                    # Register take profit and stop loss for when the limit order gets filled
                    if order_action[ORDER_ACTION__STOP_LOSS] or order_action[ORDER_ACTION__TAKE_PROFIT]:
                        (pending_orders, stop_loss_order_indice, take_profit_order_indice) = register_take_profit_stop_loss(
                            pending_orders=pending_orders,
                            order_action=order_action,
                            size=size,
                            incoming_open_price=order_action_price,  # Use limit price as reference for TP/SL
                        )

                        # Link the limit order with its TP/SL orders if they exist
                        if not np.isnan(stop_loss_order_indice):
                            pending_orders = add_oco_order_indice(
                                pending_orders=pending_orders,
                                order_indice=int(limit_order_indice),
                                oco_order_indice=int(stop_loss_order_indice)
                            )
                            pending_orders = add_oco_order_indice(
                                pending_orders=pending_orders,
                                order_indice=int(stop_loss_order_indice),
                                oco_order_indice=int(limit_order_indice)
                            )

                        if not np.isnan(take_profit_order_indice):
                            pending_orders = add_oco_order_indice(
                                pending_orders=pending_orders,
                                order_indice=int(limit_order_indice),
                                oco_order_indice=int(take_profit_order_indice)
                            )
                            pending_orders = add_oco_order_indice(
                                pending_orders=pending_orders,
                                order_indice=int(take_profit_order_indice),
                                oco_order_indice=int(limit_order_indice)
                            )

        
                if order_action_order_type == ORDER_TYPE__MARKET:
                    (pending_orders, stop_loss_order_indice, take_profit_order_indice) = register_take_profit_stop_loss(
                        pending_orders=pending_orders,
                        order_action=order_action,
                        size=size,
                        incoming_open_price=incoming_open_price,
                    )

                    (equity, position, all_pls) = applicate_order(
                        side=side,
                        size=size,
                        price=incoming_open_price,
                        current_position_size=current_position_size,
                        current_position_avg_price=current_position_avg_price,
                        current_close_price=current_close_price,
                        current_equity=equity,
                        all_pls=all_pls,
                    )


        next_pos_size = position[POSITION__SIZE]


        if next_pos_size > 0:
            next_pos_avg_price = position[POSITION__AVG_PRICE]
            next_position_pl = (incoming_open_price - next_pos_avg_price) * next_pos_size
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



@njit
def applicate_order(
    side: TSide,
    size: float,
    price: float,
    current_position_size: float,
    current_position_avg_price: float,
    current_close_price: float,
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
        next_pos_pl = (current_close_price - next_pos_avg_price) * next_pos_size
        position = (next_pos_size, next_pos_avg_price, next_pos_pl)

    return (equity, position, all_pls)



@njit
def applicate_all_pending_orders(
    pending_orders: TOrders,
    current_equity: float,
    current_position: TPosition,
    current_all_pls: np.ndarray,
    data: TOhlcv,
    i: int,
) -> tuple[float, TPosition, np.ndarray, TOrders]:
    current_close_price = data[i, OHLCV__CLOSE]


    for pending_orders_index in range(MAX_NUMBER_OF_PENDING_ORDERS):
        pending_order = pending_orders[pending_orders_index]
        pending_order_size = pending_order[ORDER__SIZE]
        

        if np.isnan(pending_order_size) or pending_order_size == 0:
            continue


        pending_order_side = pending_order[ORDER__SIDE]
        pending_order_price = pending_order[ORDER__PRICE]
        pending_order_type = pending_order[ORDER__ORDER_TYPE]

        current_low_price = data[i, OHLCV__LOW]
        current_high_price = data[i, OHLCV__HIGH]
        current_open_price = data[i, OHLCV__OPEN]
        last_close_price = data[i - 1, OHLCV__CLOSE] if i >= 1 else None

        is_price_between_last_close_and_open = (
            last_close_price is not None and 
            is_between(
                lim1=last_close_price,
                x=pending_order_price,
                lim2=current_open_price,
                strict=pending_order_type == ORDER_TYPE__LIMIT
            )
        )


        if is_price_between_last_close_and_open:                        
            pending_order_price = current_open_price


        is_triggered = False        


        if pending_order_type == ORDER_TYPE__STOP:
            is_triggered = (
                (pending_order_side == BUY and (current_high_price >= pending_order_price or is_price_between_last_close_and_open)) or
                (pending_order_side == SELL and (current_low_price <= pending_order_price or is_price_between_last_close_and_open))
            )
        elif pending_order_type == ORDER_TYPE__LIMIT:
            is_triggered = (
                current_low_price < pending_order_price < current_high_price or is_price_between_last_close_and_open
            )
        else:
            raise ValueError(f"Pending order type not limit ({ORDER_TYPE__LIMIT}) nor stop ({ORDER_TYPE__STOP}), got : {pending_order_type}")
        

        if is_triggered:
            (current_equity, current_position, current_all_pls) = applicate_order(
                side=pending_order_side,
                size=pending_order_size,
                price=pending_order_price,
                current_position_size=current_position[POSITION__SIZE],
                current_position_avg_price=current_position[POSITION__AVG_PRICE],
                current_close_price=current_close_price,
                current_equity=current_equity,
                all_pls=current_all_pls,
            )
            pending_orders[pending_orders_index].fill(np.nan)
    

    return (current_equity, current_position, current_all_pls, pending_orders)



@njit
def register_pending_order(
    order_action: TOrderAction,
    pending_orders: TPendingOrderWithOcos,
) -> tuple[TPendingOrderWithOcos, int | float]:
    order_action_price = order_action[ORDER_ACTION__PRICE]
    order_type = order_action[ORDER_ACTION__ORDER_TYPE]


    if order_type != ORDER_TYPE__LIMIT and order_type != ORDER_TYPE__STOP:
        raise ValueError(f"In register_pending_order : order type must be limit ({ORDER_TYPE__LIMIT}) or stop ({ORDER_TYPE__STOP}), got: {order_type}")


    size = order_action[ORDER_ACTION__ABSOLUTE_SIZE]


    if size == 0 or order_action_price == 0:
        print(f"Warning: order_action with absolute_size set to 0 or price set to 0 passed to register_pending_order.\
        This is not the intended use.\
        Please calculate the absolute_size and set a non-zero price before passing the order_action to register_pending_order.")
        print(order_action)
        return (pending_orders, np.nan)


    side = order_action[ORDER_ACTION__SIDE]

    next_nan_indice = get_next_pending_order_free_indice(pending_orders)

    pending_order_indice = next_nan_indice

    pending_order_tuple = make_order_tuple(
        size=size,
        stop_loss=order_action[ORDER_ACTION__STOP_LOSS],
        take_profit=order_action[ORDER_ACTION__TAKE_PROFIT],
        price=order_action_price,
        order_type=order_type,
        side=side,
        user_id=0, # no user id for now
    )

    full_order = np.full(ORDER__SHAPE[1] + MAX_NUMBER_OF_OCO_ORDERS, np.nan, dtype=np.float64)
    full_order[:len(pending_order_tuple)] = np.array(pending_order_tuple, dtype=np.float64)
    pending_orders[pending_order_indice] = full_order

    return (pending_orders, pending_order_indice)



@njit
def add_oco_order_indice(
    pending_orders: TPendingOrderWithOcos,
    order_indice: int,
    oco_order_indice: int
) -> TPendingOrderWithOcos:
    order = pending_orders[order_indice]
    base_order_len = len(TOrderKeys)
    
    for i in range(MAX_NUMBER_OF_OCO_ORDERS):
        if np.isnan(order[base_order_len + i]):
            order[base_order_len + i] = float(oco_order_indice)
            pending_orders[order_indice] = order
            return pending_orders
    
    raise ValueError(f"MAX_NUMBER_OF_OCO_ORDERS is too low. Please increase it. Current value: {MAX_NUMBER_OF_OCO_ORDERS}")


@njit
def register_take_profit_stop_loss(
    pending_orders: TPendingOrderWithOcos,
    order_action: TOrderAction,
    size: float,
    incoming_open_price: float,
) -> tuple[TPendingOrderWithOcos, float, float]:
    stop_loss_price = order_action[ORDER_ACTION__STOP_LOSS]
    take_profit_price = order_action[ORDER_ACTION__TAKE_PROFIT]
    stop_loss_order_indice = np.nan
    take_profit_order_indice = np.nan
    side = order_action[ORDER_ACTION__SIDE]
    reverse_side = get_reverse_side(side)

    if stop_loss_price:
        if side == BUY and stop_loss_price > incoming_open_price:
            print(f"Cannot place a buy stop loss order at {str(stop_loss_price)} because the incoming open price is {str(incoming_open_price)}")
            return (pending_orders, np.nan, np.nan)
        elif side == SELL and stop_loss_price < incoming_open_price:
            print(f"Cannot place a sell stop loss order at {str(stop_loss_price)} because the incoming open price is {str(incoming_open_price)}")
            return (pending_orders, np.nan, np.nan)

        (pending_orders, stop_loss_order_indice) = register_pending_order(
            order_action=make_order_action(
                absolute_size=size,
                price=stop_loss_price,
                order_type=ORDER_TYPE__STOP,
                side=reverse_side,
                stop_loss=0,
                take_profit=0,
            ),
            pending_orders=pending_orders,
        )
        if np.isnan(stop_loss_order_indice):
            raise ValueError("Failed to register stop loss order - received NaN index")

    if take_profit_price:
        if side == BUY and take_profit_price < incoming_open_price:
            print(f"Cannot place a buy take profit order at {str(take_profit_price)} because the incoming open price is {str(incoming_open_price)}")
            return (pending_orders, np.nan, np.nan)
        elif side == SELL and take_profit_price > incoming_open_price:
            print(f"Cannot place a sell take profit order at {str(take_profit_price)} because the incoming open price is {str(incoming_open_price)}")
            return (pending_orders, np.nan, np.nan)

        (pending_orders, take_profit_order_indice) = register_pending_order(
            order_action=make_order_action(
                absolute_size=size,
                price=take_profit_price,
                order_type=ORDER_TYPE__LIMIT,
                side=reverse_side,
                stop_loss=0,
                take_profit=0,
            ),
            pending_orders=pending_orders,
        )
        if np.isnan(take_profit_order_indice):
            raise ValueError("Failed to register take profit order - received NaN index")

    if not np.isnan(stop_loss_order_indice) and not np.isnan(take_profit_order_indice):
        pending_orders = add_oco_order_indice(
            pending_orders=pending_orders,
            order_indice=int(stop_loss_order_indice),
            oco_order_indice=int(take_profit_order_indice)
        )
        pending_orders = add_oco_order_indice(
            pending_orders=pending_orders,
            order_indice=int(take_profit_order_indice),
            oco_order_indice=int(stop_loss_order_indice)
        )

    return (pending_orders, stop_loss_order_indice, take_profit_order_indice)