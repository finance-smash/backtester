import unittest
import talib
import numpy as np
import time

from backtester.commons import get_ohlcv_data, BUY_SIGNAL, NO_SIGNAL, SELL_SIGNAL, OHLCV__CLOSE,\
    TOhlcv, ORDER_TYPE__LIMIT, OFFSET__CLOSE, OFFSET__OPEN, TSide,\
    OHLCV__OPEN, OHLCV__HIGH, OHLCV__LOW
from backtester.order_action import TOrderActions, make_order_action_tuple 
from backtester.strategy import Strategy, TStrategyParams, backtest_strategy, cancel_pending_order_at_index, make_backtest_setup_tuple
from backtester.order import TOrders, ORDER__SIZE
from backtester.position import POSITION__PL, TPositionTripleArray, POSITION__SIZE


DEBUG = False

def indicators_fn(data: TOhlcv, params: TStrategyParams) -> np.ndarray:
    open = data[:, OHLCV__OPEN]
    high = data[:, OHLCV__HIGH]
    low = data[:, OHLCV__LOW]
    close = data[:, OHLCV__CLOSE]
    short_ma = talib.SMA(data[:, OHLCV__CLOSE], timeperiod=20)
    long_ma = talib.SMA(data[:, OHLCV__CLOSE], timeperiod=200)
    short_bollinger_bands = talib.BBANDS(data[:, OHLCV__CLOSE], timeperiod=20, nbdevup=2, nbdevdn=2, matype=talib.MA_Type.SMA)
    short_bollinger_bands_upper = short_bollinger_bands[0]
    short_bollinger_bands_middle = short_bollinger_bands[1]
    short_bollinger_bands_lower = short_bollinger_bands[2]

    price_above_long_ma = data[:, OHLCV__CLOSE] > long_ma
    price_below_long_ma = data[:, OHLCV__CLOSE] < long_ma

    return np.array([
        short_ma,
        long_ma,
        short_bollinger_bands_upper,
        short_bollinger_bands_middle,
        short_bollinger_bands_lower,
        price_above_long_ma,
        price_below_long_ma,
        close,
        open,
        high,
        low
    ])



def order_fn(
    indicators: np.ndarray,
    index: int,
    params: TStrategyParams,
    pending_orders: TOrders,
    position_triple: TPositionTripleArray,
    state: np.ndarray
) -> tuple[TOrderActions, np.ndarray]:
    short_ma = indicators[0]
    short_bollinger_bands_upper = indicators[2]
    short_bollinger_bands_lower = indicators[4]
    price_above_long_ma = indicators[5]
    price_below_long_ma = indicators[6]
    close = indicators[7]


    short_ma_at_index = short_ma[index]
    short_bollinger_bands_upper_at_index = short_bollinger_bands_upper[index]
    short_bollinger_bands_lower_at_index = short_bollinger_bands_lower[index]
    price_above_long_ma_at_index = price_above_long_ma[index]
    price_below_long_ma_at_index = price_below_long_ma[index]
    close_at_index = close[index]

    hedging_long_position = position_triple[1]
    hedging_short_position = position_triple[2]

    position_long_size = hedging_long_position[POSITION__SIZE]
    position_short_size = hedging_short_position[POSITION__SIZE]

    position_long_is_open = position_long_size != 0
    position_short_is_open = position_short_size != 0

    pending_order_len = len(pending_orders)

    is_there_a_pending_order = False
    for i in range(pending_order_len):
        pending_order = pending_orders[i]
        order_size = pending_order[ORDER__SIZE]
        if not np.isnan(order_size):
            is_there_a_pending_order = True
            break

    if is_there_a_pending_order:
        for i in range(pending_order_len):
            pending_order = pending_orders[i]
            order_size = pending_order[ORDER__SIZE]
            if not np.isnan(order_size):
                cancel_pending_order_at_index(
                    pending_orders=pending_orders,
                    pending_order_index=i
                )


    order_actions = []


    if position_long_is_open:
        next_limit_close = max(short_ma_at_index, close_at_index + 1)
        long_close_order_action = make_order_action_tuple(
            relative_size=0.,
            absolute_size=np.abs(position_long_size),
            offset=OFFSET__CLOSE,
            price=next_limit_close,
            order_type=ORDER_TYPE__LIMIT,
            side=SELL_SIGNAL,
            user_id=0
        )
        order_actions.append(long_close_order_action)


    if position_short_is_open:
        next_limit_close = min(short_ma_at_index, close_at_index - 1)
        short_close_order_action = make_order_action_tuple(
            relative_size=0.,
            absolute_size=np.abs(position_short_size),
            offset=OFFSET__CLOSE,
            price=next_limit_close,
            order_type=ORDER_TYPE__LIMIT,
            side=BUY_SIGNAL,
            user_id=0
        )
        order_actions.append(short_close_order_action)


    signal_at_index: TSide = NO_SIGNAL


    if price_above_long_ma_at_index and close_at_index > short_bollinger_bands_lower_at_index:
        signal_at_index = BUY_SIGNAL
    elif price_below_long_ma_at_index and close_at_index < short_bollinger_bands_upper_at_index:
        signal_at_index = SELL_SIGNAL


    if signal_at_index == BUY_SIGNAL:
        order_actions.append(make_order_action_tuple(
            relative_size=0.,
            absolute_size=1.,
            take_profit=short_ma_at_index,
            price=short_bollinger_bands_lower_at_index,
            order_type=ORDER_TYPE__LIMIT,
            side=BUY_SIGNAL,
            offset=OFFSET__OPEN,
            user_id=0
        ))
    elif signal_at_index == SELL_SIGNAL:
        order_actions.append(make_order_action_tuple(
            relative_size=0.,
            absolute_size=1.,
            take_profit=short_ma_at_index,
            price=short_bollinger_bands_upper_at_index,
            order_type=ORDER_TYPE__LIMIT,
            side=SELL_SIGNAL,
            offset=OFFSET__OPEN,
            user_id=0
        ))


    np_arr_actions = np.array(order_actions, dtype=np.float64) if len(order_actions) > 0 else np.empty((0, 7), dtype=np.float64)

    return (np_arr_actions, state)



MyStrategy = Strategy(
    default_params=np.array([]),
    indicators_fn=indicators_fn,
    order_fn=order_fn
)



class WithOpenLimitAndCancellationLimit(unittest.TestCase):
    ohlcv = get_ohlcv_data('crypto', 'BTC-USDT', '15min', "/Users/dyodio/Documents/Projects/Finance-Smash/backtester/tests/__data__")
    # ohlcv = ohlcv[:20000]
    ohlcv = ohlcv[:500]
    begin_equity = 100_000_000_00
    backtest_setup = make_backtest_setup_tuple(
        begin_equity=begin_equity,
        is_hedged=1,
        auto_trigger_tp_sl=True
    )

    backtest_strategy(
        strategy=MyStrategy,
        data=ohlcv,
        setup=backtest_setup,
        params=np.array([]),
        state_shape=(0,)
    )

    start_time = time.time()

    result_info = backtest_strategy(
        strategy=MyStrategy,
        data=ohlcv,
        setup=backtest_setup,
        params=np.array([]),
        state_shape=(0,)
    )

    end_time = time.time()

    time_taken = end_time - start_time

    final_equity = result_info[2]
    final_equity_rounded = round(final_equity, 2)
    position_triple = result_info[0]
    all_pls = result_info[3]

    pls_from_position_triple = np.nan_to_num(position_triple[:, POSITION__PL]).sum()
    final_gain_with_last_pls = pls_from_position_triple + final_equity - begin_equity
    final_gain_with_last_pls_rounded = round(final_gain_with_last_pls, 2)

    print(f"Time taken: {time_taken} seconds")
    print(f"Final equity: {final_equity_rounded}")
    print(f"Final gain: {final_equity - begin_equity}")
    print(f"All pls length: {len(all_pls)}")
    print("Final gain with last pls:", final_gain_with_last_pls_rounded)

    def test_result_is_expected(self):
        self.assertEqual(self.final_gain_with_last_pls_rounded, 806.9)


if __name__ == '__main__':
    unittest.main()