import numpy as np
import numpy.typing as npt

from typing import Annotated, Literal
from numba import njit # type: ignore

from backtester.commons import BUY, SELL, NO_SIDE, TOhlcv, OHLCV__OPEN, OHLCV__CLOSE, OHLCV__LOW, OHLCV__HIGH, TSide, get_reverse_side, \
    MAX_NUMBER_OF_PENDING_ORDERS, MAX_NUMBER_OF_OCO_ORDERS, ORDER_TYPE__LIMIT, ORDER_TYPE__MARKET, ORDER_TYPE__STOP, OFFSET__CLOSE, \
    OFFSET__BOTH, TOffset, TBoolInt
from backtester.order import TOrders, ORDER__SHAPE, ORDER__SIDE, ORDER__SIZE, ORDER__PRICE, ORDER__ORDER_TYPE,\
    TOrderTuple, make_order_tuple, TOrderKeys, \
    ORDER__STOP_LOSS, ORDER__TAKE_PROFIT, ORDER__OFFSET, ORDER__CANDLE_INDEX
from backtester.order_action import ORDER_ACTION__ABSOLUTE_SIZE, ORDER_ACTION__SIDE, ORDER_ACTION__PRICE, ORDER_ACTION__ORDER_TYPE, \
    ORDER_ACTION__STOP_LOSS, ORDER_ACTION__TAKE_PROFIT, TOrderAction, make_order_action, ORDER_ACTION__OFFSET
from backtester.position import POSITION__AVG_PRICE, POSITION__SIZE, get_position_side, TPositionTripleArray, TPositionArray

from backtester.strategy.strategy import Strategy, TStrategyParams, TOrderFn



DEBUG = False
BASE_ORDER_LEN = len(TOrderKeys)

TPendingOrderWithOco = Annotated[
    npt.NDArray[np.float64],
    TOrderTuple,
    MAX_NUMBER_OF_OCO_ORDERS,
] # The ocos at the end of the order need to be contiguous : e.g : [...TOrderTuple, 0 (first oco), 1 (second oco), 2 (third oco), np.nan (no more ocos after this), np.nan, np.nan, ..., np.nan] (all ocos contiguous then all nan)

TPendingOrderWithOcos = Annotated[
    TPendingOrderWithOco,
    Literal["N"]
]

TBacktestSetupTuple = tuple[
    float, # cash
    TBoolInt, # is_hedged
    bool, # auto_trigger_tp_sl
]

TBacktestSetup = TBacktestSetupTuple

TBacktestResultTuple = tuple[
    TPositionTripleArray, # last position triple
    int, # number of orders
    float, # final equity
    np.ndarray, # all pls as an array of (pl, pl_perc, pl_size, pl_close_price, pl_avg_price),
    np.ndarray # state
]

TBacktestResult = TBacktestResultTuple



@njit
def make_backtest_setup_tuple(
    begin_equity: float,
    is_hedged: TBoolInt,
    auto_trigger_tp_sl: bool,
) -> TBacktestSetupTuple:
    return (begin_equity, is_hedged, auto_trigger_tp_sl)



def backtest_strategy(
    strategy: Strategy,
    data: TOhlcv,
    setup: TBacktestSetup,
    params: TStrategyParams,
    state_shape: tuple[int] = (0,)
):
    indicators = strategy.indicators_fn(data, params)
    return backtest_strategy_loop(indicators, strategy.order_fn, data, setup, params, state_shape)



@njit
def backtest_strategy_loop(
    indicators: np.ndarray,
    order_fn: TOrderFn,
    data: TOhlcv,
    setup: TBacktestSetup,
    params: TStrategyParams,
    state_shape: tuple[int] = (0,)
) -> TBacktestResult:
    data_len = len(data)
    nb_of_orders = 0
    (equity, is_hedged_boolint, auto_trigger_tp_sl) = setup
    is_hedged = is_hedged_boolint == 1
    position_triple = np.zeros((3, 3), dtype=np.float64)


    if is_hedged:
        position_triple[0].fill(np.nan)
    else:
        position_triple[1].fill(np.nan)
        position_triple[2].fill(np.nan)


    pending_orders: TPendingOrderWithOcos = np.empty(
        (MAX_NUMBER_OF_PENDING_ORDERS, ORDER__SHAPE[1] + MAX_NUMBER_OF_OCO_ORDERS),
        dtype=np.float64
    )
    pending_orders.fill(np.nan)
    all_pls = np.empty((0, 5), dtype=np.float64) #[[pl, pl_perc, pl_size, pl_close_price, pl_avg_price]]
    state = np.zeros(state_shape, dtype=np.float64)
    state.fill(np.nan)


    for i in range(data_len - 1):
        (
            equity,
            position_triple,
            all_pls,
            pending_orders
        ) = applicate_all_pending_orders(
            pending_orders=pending_orders,
            current_equity=equity,
            current_position_triple=position_triple,
            current_all_pls=all_pls,
            data=data,
            is_hedged=is_hedged,
            auto_trigger_tp_sl=auto_trigger_tp_sl,
            i=i
        )

        current_close_price = data[i, OHLCV__CLOSE]
        incoming_open_price = data[i + 1, OHLCV__OPEN]
        (order_actions, state) = order_fn(indicators, i, params, pending_orders, position_triple, state)
        order_actions_len = len(order_actions)


        if order_actions_len > 0:
            nb_of_orders += order_actions_len


            for order_action_index in range(order_actions_len):
                order_action: TOrderAction = order_actions[order_action_index]
                absolute_size = order_action[ORDER_ACTION__ABSOLUTE_SIZE]
                side: TSide = order_action[ORDER_ACTION__SIDE]
                size: float = 0.0


                if absolute_size > 0:
                    size = absolute_size
                else:
                    raise ValueError("Only absolute size is accepted for now")
                
                
                order_action[ORDER_ACTION__ABSOLUTE_SIZE] = size
                order_action_price = order_action[ORDER_ACTION__PRICE]
                order_action_order_type = order_action[ORDER_ACTION__ORDER_TYPE]
                order_action_stop_loss = order_action[ORDER_ACTION__STOP_LOSS]
                order_action_take_profit = order_action[ORDER_ACTION__TAKE_PROFIT]
                order_action_offset = order_action[ORDER_ACTION__OFFSET]


                if order_action_order_type == ORDER_TYPE__LIMIT:
                    if side == BUY and order_action_price >= current_close_price:
                        raise ValueError(f"Cannot place a buy limit order at", order_action_price, "because the last close price is", current_close_price)
                    elif side == SELL and order_action_price <= current_close_price:
                        raise ValueError(f"Cannot place a sell limit order at", order_action_price, "because the last close price is", current_close_price, "index", i)
                    

                    (pending_orders, limit_order_index) = register_pending_order(
                        order_action=make_order_action(
                            absolute_size=size,
                            price=order_action_price,
                            order_type=ORDER_TYPE__LIMIT,
                            side=side,
                            stop_loss=order_action_stop_loss,
                            take_profit=order_action_take_profit,
                            offset=order_action_offset,
                        ),
                        pending_orders=pending_orders,
                        candle_index=i
                    )


                    if np.isnan(limit_order_index):
                        raise ValueError("Failed to register limit order - received NaN index")

        
                if order_action_order_type == ORDER_TYPE__MARKET:
                    if DEBUG:
                        print(f"Market order at index {i}")
                        print("Order side", side)
                        print("Order stop loss", order_action_stop_loss)
                        print("Order take profit", order_action_take_profit)
                        print("Order size", size)
                        print("incoming open price", incoming_open_price)
                    # TO DO: check if the tp/sl can be placed, e.g in case of a long if the tp is lower than the incoming open price, it cannot be placed
                    (pending_orders, _, _) = register_take_profit_stop_loss(
                        pending_orders=pending_orders,
                        side=side,
                        stop_loss=order_action_stop_loss,
                        take_profit=order_action_take_profit,
                        size=size,
                        candle_index=i
                    )

                    (equity, position_triple, all_pls, pending_orders) = applicate_order(
                        side=side,
                        size=size,
                        price=incoming_open_price,
                        position_triple=position_triple,
                        current_close_price=current_close_price,
                        current_equity=equity,
                        all_pls=all_pls,
                        pending_orders=pending_orders,
                        offset=order_action_offset,
                        is_hedged=is_hedged,
                        i=i,
                    )


        for position_index in range(3):
            current_position = position_triple[position_index]
            next_pos_size = current_position[POSITION__SIZE]


            if not np.isnan(next_pos_size) and next_pos_size != 0:
                next_pos_avg_price = current_position[POSITION__AVG_PRICE]
                next_position_pl = (incoming_open_price - next_pos_avg_price) * next_pos_size
                next_current_position: TPositionArray = np.array([next_pos_size, next_pos_avg_price, next_position_pl], dtype=np.float64)
                position_triple[position_index] = next_current_position


    return (position_triple, nb_of_orders, equity, all_pls, state)



@njit
def applicate_all_pending_orders(
    pending_orders: TOrders,
    current_equity: float,
    current_position_triple: TPositionTripleArray,
    current_all_pls: np.ndarray,
    data: TOhlcv,
    is_hedged: bool,
    auto_trigger_tp_sl: bool,
    i: int,
) -> tuple[float, TPositionTripleArray, np.ndarray, TOrders]:
    current_close_price = data[i, OHLCV__CLOSE]
    incoming_open_price = data[i + 1, OHLCV__OPEN]
    first_pending_order_index = -1


    for pending_orders_index in range(MAX_NUMBER_OF_PENDING_ORDERS):
        pending_order = pending_orders[pending_orders_index]
        pending_order_size = pending_order[ORDER__SIZE]
        if not np.isnan(pending_order_size) and pending_order_size != 0:
            first_pending_order_index = int(pending_orders_index)
            break


    if first_pending_order_index == -1:
        return (current_equity, current_position_triple, current_all_pls, pending_orders)
    

    for pending_orders_index in range(first_pending_order_index, MAX_NUMBER_OF_PENDING_ORDERS):
        pending_order = pending_orders[pending_orders_index]
        pending_order_size = pending_order[ORDER__SIZE]
        pending_order_candle_index = pending_order[ORDER__CANDLE_INDEX]
        

        if (
            pending_order_candle_index >= i or
            np.isnan(pending_order_size) or 
            pending_order_size == 0
        ):
            continue


        pending_order_side = pending_order[ORDER__SIDE]
        pending_order_price = pending_order[ORDER__PRICE]
        pending_order_type = pending_order[ORDER__ORDER_TYPE]
        pending_order_stop_loss = pending_order[ORDER__STOP_LOSS]
        pending_order_take_profit = pending_order[ORDER__TAKE_PROFIT]
        pending_order_offset = pending_order[ORDER__OFFSET]
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


        is_triggered = is_order_triggered(
            pending_order_type=pending_order_type,
            pending_order_side=pending_order_side,
            pending_order_price=pending_order_price,
            current_high_price=current_high_price,
            current_low_price=current_low_price,
            is_price_between_last_close_and_open=is_price_between_last_close_and_open,
        )

        if is_triggered and DEBUG:
            print(f"{'Limit' if pending_order_type == ORDER_TYPE__LIMIT else 'Stop'} order triggered at candle index {i}", "pending order price", pending_order_price, "pending_orders_index", pending_orders_index, "ori pending order price", pending_order[ORDER__PRICE])
        

        if is_triggered:
            is_pending_tp_auto_triggered = False
            is_pending_sl_auto_triggered = False
            if (pending_order_stop_loss or pending_order_take_profit):
                reverse_side = get_reverse_side(pending_order_side)
                if pending_order_take_profit and auto_trigger_tp_sl:
                    candle_is_same_side_buy = (pending_order_side == BUY and current_open_price < current_close_price)
                    candle_is_same_side_sell = (pending_order_side == SELL and current_open_price > current_close_price)
                    is_pending_tp_auto_triggered_after_open_at_open = is_price_between_last_close_and_open and is_order_triggered(
                        pending_order_type=ORDER_TYPE__LIMIT,
                        pending_order_side=reverse_side,
                        pending_order_price=pending_order_take_profit,
                        current_high_price=current_high_price,
                        current_low_price=current_low_price,
                        is_price_between_last_close_and_open=False,
                    )
                    is_pending_tp_auto_triggered_side_buy = candle_is_same_side_buy and is_order_triggered(
                        pending_order_type=ORDER_TYPE__LIMIT,
                        pending_order_side=reverse_side,
                        pending_order_price=pending_order_take_profit,
                        current_high_price=current_close_price,
                        current_low_price=current_low_price,
                        is_price_between_last_close_and_open=False,
                    )
                    is_pending_tp_auto_triggered_side_sell = candle_is_same_side_sell and is_order_triggered(
                        pending_order_type=ORDER_TYPE__LIMIT,
                        pending_order_side=reverse_side,
                        pending_order_price=pending_order_take_profit,
                        current_high_price=current_high_price,
                        current_low_price=current_close_price,
                        is_price_between_last_close_and_open=False,
                    )
                    is_pending_tp_auto_triggered = (
                        is_pending_tp_auto_triggered_after_open_at_open or
                        is_pending_tp_auto_triggered_side_buy or
                        is_pending_tp_auto_triggered_side_sell
                    )
                
                if pending_order_stop_loss and auto_trigger_tp_sl:
                    final_sl_price = min(pending_order_stop_loss, pending_order_price) if pending_order_side == BUY else max(pending_order_stop_loss, pending_order_price)
                    if final_sl_price != pending_order_stop_loss:
                        print("Warning: Stop loss price has been modified to", final_sl_price, "from", pending_order_stop_loss, "this can happen if there is a big jump in candles")
                        pending_order_stop_loss = final_sl_price
                    is_pending_sl_auto_triggered = is_order_triggered(
                        pending_order_type=ORDER_TYPE__STOP,
                        pending_order_side=reverse_side,
                        pending_order_price=pending_order_stop_loss,
                        current_high_price=current_high_price,
                        current_low_price=current_low_price,
                        is_price_between_last_close_and_open=False,
                    )

                if (not is_pending_tp_auto_triggered) and (not is_pending_sl_auto_triggered):
                    (pending_orders, _, _) = register_take_profit_stop_loss(
                        pending_orders=pending_orders,
                        side=pending_order_side,
                        stop_loss=pending_order_stop_loss,
                        take_profit=pending_order_take_profit,
                        size=pending_order_size,
                        candle_index=i
                    )


            pending_orders = cancel_pending_order_at_index(pending_orders, pending_orders_index)

            (current_equity, current_position_triple, current_all_pls, pending_orders) = applicate_order(
                side=pending_order_side,
                size=pending_order_size,
                price=pending_order_price,
                position_triple=current_position_triple,
                current_close_price=current_close_price,
                current_equity=current_equity,
                all_pls=current_all_pls,
                pending_orders=pending_orders,
                offset=pending_order_offset,
                is_hedged=is_hedged,
                i=i,
            )

            if is_pending_sl_auto_triggered:
                if DEBUG:
                    print(f"Stop loss order auto triggered at candle index {i}", "pending_order_stop_loss_price", pending_order_stop_loss, "pending_orders_index", pending_orders_index)
                (current_equity, current_position_triple, current_all_pls, pending_orders) = applicate_order(
                    side=reverse_side,
                    size=pending_order_size,
                    price=pending_order_stop_loss,
                    position_triple=current_position_triple,
                    current_close_price=current_close_price,
                    current_equity=current_equity,
                    all_pls=current_all_pls,
                    pending_orders=pending_orders,
                    offset=OFFSET__CLOSE,
                    is_hedged=is_hedged,
                    i=i,
                )

            elif is_pending_tp_auto_triggered:
                if DEBUG:
                    print(f"Take profit order auto triggered at candle index {i}", "pending_order_take_profit_price", pending_order_take_profit, "pending_orders_index", pending_orders_index)
                (current_equity, current_position_triple, current_all_pls, pending_orders) = applicate_order(
                    side=reverse_side,
                    size=pending_order_size,
                    price=pending_order_take_profit,
                    position_triple=current_position_triple,
                    current_close_price=current_close_price,
                    current_equity=current_equity,
                    all_pls=current_all_pls,
                    pending_orders=pending_orders,
                    offset=OFFSET__CLOSE,
                    is_hedged=is_hedged,
                    i=i,
                )
    

    return (current_equity, current_position_triple, current_all_pls, pending_orders)



@njit
def cancel_pending_offset_close_orders(
    pending_orders: TOrders,
    position_index: int,
    next_pos_side: int,
    is_hedged: bool
) -> TOrders:
    for pending_order_index in range(MAX_NUMBER_OF_PENDING_ORDERS):
        pending_order = pending_orders[pending_order_index]
        pending_order_size = pending_order[ORDER__SIZE]
        pending_order_side = pending_order[ORDER__SIDE]
        pending_order_offset = pending_order[ORDER__OFFSET]
        
        order_corresponding_position_index = get_position_triple_index_for_order(
            is_hedged=is_hedged,
            order_side=pending_order_side,
            order_offset=pending_order_offset
        )

        if order_corresponding_position_index != position_index or \
            np.isnan(pending_order_size) or \
            pending_order_size == 0 or \
            pending_order_offset != OFFSET__CLOSE:
            continue

        if next_pos_side != SELL and pending_order_side == BUY:
            if DEBUG:
                print(f"Cancelling long close order at index {pending_order_index}")
            pending_orders = cancel_pending_order_at_index(pending_orders, pending_order_index)
        elif next_pos_side != BUY and pending_order_side == SELL:
            if DEBUG:
                print(f"Cancelling short close order at index {pending_order_index}")
            pending_orders = cancel_pending_order_at_index(pending_orders, pending_order_index)

    return pending_orders



@njit
def applicate_order(
    side: TSide,
    size: float,
    price: float,
    position_triple: TPositionTripleArray,
    current_close_price: float,
    current_equity: float,
    all_pls: np.ndarray,
    pending_orders: TOrders,
    offset: TOffset = OFFSET__BOTH,
    is_hedged: bool = False,
    i = 0,
):
    equity = current_equity
    position_index = 0


    if is_hedged:
        if (side == BUY and offset != OFFSET__CLOSE) or (side == SELL and offset == OFFSET__CLOSE):
            position_index = 1
        elif (side == SELL and offset != OFFSET__CLOSE) or (side == BUY and offset == OFFSET__CLOSE):
            position_index = 2


    current_position = position_triple[position_index]
    current_position_size = current_position[POSITION__SIZE]
    current_position_abs_size = np.abs(current_position_size)


    if offset == OFFSET__CLOSE and size > current_position_abs_size:
        print("Cannot close a position with a size greater than the current position size. This problem often occurs when the take profit and stop loss are triggered at the same candle.")
        return (equity, position_triple, all_pls, pending_orders)


    current_position_avg_price = current_position[POSITION__AVG_PRICE]
    current_position_side = get_position_side(current_position_size)
    side_sign = -1 if side == SELL else 1 if side == BUY else 0
    price_to_pay = size * price
    next_pos_size = current_position_size + side_sign * size
    next_pos_side = get_position_side(next_pos_size)
    next_pos_avg_price = current_position_avg_price
    position_changed_side = current_position_side != next_pos_side
    order_same_side = side == current_position_side


    pending_orders = cancel_pending_offset_close_orders(
        pending_orders=pending_orders,
        position_index=position_index,
        next_pos_side=next_pos_side,
        is_hedged=is_hedged
    )


    next_position: TPositionArray = np.array([0., 0., 0.], dtype=np.float64)


    if next_pos_size == 0:
        final_pos_pl = (price - current_position_avg_price) * current_position_size
        equity += final_pos_pl


        if DEBUG:
            print("--------------------------------")
            print(f"i", i)
            print(f"Final pos pl", final_pos_pl)
            print("position_index", position_index)
            print("current_position_avg_price", current_position_avg_price)
            print("price", price)
            print("--------------------------------")

        pl_perc = ((price - current_position_avg_price) / current_position_avg_price) * np.sign(current_position_size)
        all_pls = np.vstack(
            (
                all_pls,
                np.array([[
                    final_pos_pl,
                    pl_perc,
                    current_position_size,
                    price,
                    current_position_avg_price,
                ]], dtype=np.float64)
            )
        )
        next_position = np.array([0., 0., 0.], dtype=np.float64)
    else:
        if position_changed_side:
            (next_pos_avg_price, equity, all_pls) = handle_position_side_change(
                current_position_side=current_position_side,
                next_pos_side=next_pos_side,
                current_position_size=current_position_size,
                next_pos_size=next_pos_size,
                price=price,
                current_position_avg_price=current_position_avg_price,
                equity=equity,
                all_pls=all_pls
            )
        else:
            if order_same_side:
                next_pos_avg_price = (
                    current_position_avg_price * np.abs(current_position_size) + price_to_pay
                ) / np.abs(next_pos_size)
            else:
                current_position_side_sign = -1 if current_position_side == SELL else 1 if current_position_side == BUY else 0
                reduced_size = np.abs(next_pos_size - current_position_size)
                reduced_size_with_sign = reduced_size * current_position_side_sign
                reduced_size_pl = (price - current_position_avg_price) * reduced_size_with_sign
                reduced_size_pl_perc = ((price - current_position_avg_price) / current_position_avg_price) * current_position_side_sign
                equity += reduced_size_pl
                if DEBUG:
                    print("--------------------------------")
                    print(f"i", i)
                    print(f"reduced_size_pl", reduced_size_pl)
                    print("position_index", position_index)
                    print("current_position_avg_price", current_position_avg_price)
                    print("price", price)
                    print("next_pos_size", next_pos_size)
                    print("current_position_size", current_position_size)
                    print("--------------------------------")
                all_pls = np.vstack(
                    (
                        all_pls,
                        np.array([[
                            reduced_size_pl,
                            reduced_size_pl_perc,
                            reduced_size_with_sign,
                            price,
                            current_position_avg_price,
                        ]], dtype=np.float64)
                    )
                )


        next_pos_pl = (current_close_price - next_pos_avg_price) * next_pos_size
        next_position = np.array([next_pos_size, next_pos_avg_price, next_pos_pl], dtype=np.float64)


    position_triple[position_index] = next_position
    return (equity, position_triple, all_pls, pending_orders)



@njit
def handle_position_side_change(
    current_position_side: int,
    next_pos_side: int,
    current_position_size: float,
    next_pos_size: float,
    price: float,
    current_position_avg_price: float,
    equity: float,
    all_pls: np.ndarray
) -> tuple[float, float, np.ndarray]:
    if current_position_side != NO_SIDE and next_pos_side != NO_SIDE:
        size_to_close = np.abs(next_pos_size - current_position_size)
        pl_perc = ((price - current_position_avg_price) / current_position_avg_price) * np.sign(size_to_close)
        to_close_pl_with_next_open = (price - current_position_avg_price) * size_to_close
        equity += to_close_pl_with_next_open
        new_pl = np.array([[
            to_close_pl_with_next_open,
            pl_perc,
            size_to_close,
            price,
            current_position_avg_price,
        ]], dtype=np.float64)
        all_pls = np.vstack((all_pls, new_pl))
    
    return (price, equity, all_pls)



@njit
def register_take_profit_stop_loss(
    pending_orders: TPendingOrderWithOcos,
    side: TSide,
    stop_loss: float,
    take_profit: float,
    size: float,
    candle_index: int = 0
) -> tuple[TPendingOrderWithOcos, float, float]:
    stop_loss_price = stop_loss
    take_profit_price = take_profit
    stop_loss_order_index = np.nan
    take_profit_order_index = np.nan
    reverse_side = get_reverse_side(side)


    if stop_loss_price:
        (pending_orders, stop_loss_order_index) = register_pending_order(
            order_action=make_order_action(
                absolute_size=size,
                price=stop_loss_price,
                order_type=ORDER_TYPE__STOP,
                side=reverse_side,
                stop_loss=0,
                take_profit=0,
                offset=OFFSET__CLOSE
            ),
            pending_orders=pending_orders,
            candle_index=candle_index
        )


        if np.isnan(stop_loss_order_index):
            raise ValueError("Failed to register stop loss order - received NaN index")
        

        if DEBUG:
            print(f"Stop loss order registered at index", stop_loss_order_index, "and price", stop_loss_price)


    if take_profit_price:
        (pending_orders, take_profit_order_index) = register_pending_order(
            order_action=make_order_action(
                absolute_size=size,
                price=take_profit_price,
                order_type=ORDER_TYPE__LIMIT,
                side=reverse_side,
                stop_loss=0,
                take_profit=0,
                offset=OFFSET__CLOSE,
            ),
            pending_orders=pending_orders,
            from_end=True,
            candle_index=candle_index
        )


        if np.isnan(take_profit_order_index):
            raise ValueError("Failed to register take profit order - received NaN index")
        

        if DEBUG:
            print(f"Take profit order registered at index", take_profit_order_index, "and price", take_profit_price)


    if not np.isnan(stop_loss_order_index) and not np.isnan(take_profit_order_index):
        pending_orders = add_oco_order_index(
            pending_orders=pending_orders,
            pending_order_index=int(stop_loss_order_index),
            oco_order_index=int(take_profit_order_index)
        )
        pending_orders = add_oco_order_index(
            pending_orders=pending_orders,
            pending_order_index=int(take_profit_order_index),
            oco_order_index=int(stop_loss_order_index)
        )


    return (pending_orders, stop_loss_order_index, take_profit_order_index)



@njit
def register_pending_order(
    order_action: TOrderAction,
    pending_orders: TPendingOrderWithOcos,
    from_end: bool = False,
    candle_index: int = 0
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

    next_nan_index = get_next_pending_order_free_index(pending_orders, from_end)

    pending_order_index = next_nan_index

    pending_order_tuple = make_order_tuple(
        size=size,
        stop_loss=order_action[ORDER_ACTION__STOP_LOSS],
        take_profit=order_action[ORDER_ACTION__TAKE_PROFIT],
        price=order_action_price,
        order_type=order_type,
        side=side,
        offset=order_action[ORDER_ACTION__OFFSET],
        candle_index=candle_index,
        user_id=0, # no user id for now
    )

    full_order = np.full(ORDER__SHAPE[1] + MAX_NUMBER_OF_OCO_ORDERS, np.nan, dtype=np.float64)
    full_order[:len(pending_order_tuple)] = np.array(pending_order_tuple, dtype=np.float64)
    pending_orders[pending_order_index] = full_order

    if DEBUG:
        print("order registered at pending_order_index", pending_order_index, "order_type", order_type, "size", size, "price", order_action_price, "side", side, "offset", order_action[ORDER_ACTION__OFFSET])

    return (pending_orders, pending_order_index)



@njit
def add_oco_order_index(
    pending_orders: TPendingOrderWithOcos,
    pending_order_index: int,
    oco_order_index: int
) -> TPendingOrderWithOcos:
    pending_order = pending_orders[pending_order_index]


    for i in range(MAX_NUMBER_OF_OCO_ORDERS):
        oco_to_append_index = BASE_ORDER_LEN + i
        if np.isnan(pending_order[oco_to_append_index]):
            pending_order[oco_to_append_index] = float(oco_order_index)
            pending_orders[pending_order_index] = pending_order
            return pending_orders
    

    raise ValueError(f"MAX_NUMBER_OF_OCO_ORDERS is too low. Please increase it. Current value: {MAX_NUMBER_OF_OCO_ORDERS}")



@njit
def get_pending_order_ocos(pending_order_with_oco: TPendingOrderWithOco):
    return pending_order_with_oco[BASE_ORDER_LEN:]



@njit
def get_next_pending_order_free_index(pending_orders: TPendingOrderWithOcos, from_end: bool = False):
    pending_orders_isnans = np.isnan(pending_orders[:,0])
    next_nan_index = np.argmax(pending_orders_isnans) if not from_end else (MAX_NUMBER_OF_PENDING_ORDERS - 1 - np.argmax(pending_orders_isnans[::-1]))


    if next_nan_index == 0 and not np.isnan(pending_orders[0, ORDER__SIZE]):
        raise ValueError(f"MAX_NUMBER_OF_PENDING_ORDERS is too low. Please increase it. Current value: {MAX_NUMBER_OF_PENDING_ORDERS}")
    

    return int(next_nan_index)



@njit
def cancel_pending_order_at_index(pending_orders: TPendingOrderWithOcos, pending_order_index: int):
    if np.isnan(pending_order_index):
        return pending_orders
    if DEBUG:
        print(f"Cancelling pending order at index {pending_order_index}")
    pending_order = pending_orders[pending_order_index]
    pending_order_ocos = get_pending_order_ocos(pending_order).copy()
    pending_order.fill(np.nan)
    for oco_index in pending_order_ocos:
        if np.isnan(oco_index):
            break
        oco_index = int(oco_index)
        pending_orders = cancel_pending_order_at_index(pending_orders, oco_index)
    return pending_orders



@njit
def get_position_triple_index_for_order(is_hedged: bool, order_side: TSide, order_offset: TOffset):
    position_index = 0


    if is_hedged:
        if (order_side == BUY and order_offset != OFFSET__CLOSE) or (order_side == SELL and order_offset == OFFSET__CLOSE):
            position_index = 1
        elif (order_side == SELL and order_offset != OFFSET__CLOSE) or (order_side == BUY and order_offset == OFFSET__CLOSE):
            position_index = 2


    return position_index



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
def is_order_triggered(
    pending_order_type: int,
    pending_order_side: int,
    pending_order_price: float,
    current_high_price: float,
    current_low_price: float,
    is_price_between_last_close_and_open: bool,
) -> bool:
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
    
    return is_triggered