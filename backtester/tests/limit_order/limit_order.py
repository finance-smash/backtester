import unittest
import talib
import numpy as np
import time

from backtester.commons import get_ohlcv_data, BUY_SIGNAL, NO_SIGNAL, SELL_SIGNAL, OHLCV__CLOSE, TOhlcv, ORDER_TYPE__LIMIT
from backtester.order_action import TOrderActions, make_order_action_tuple 
from backtester.strategy import Strategy, TStrategyParams, backtest_strategy
from backtester.order import TOrders



def indicators_fn(data: TOhlcv, params: TStrategyParams) -> np.ndarray:
    close = data[:, OHLCV__CLOSE]
    short_ema = talib.SMA(close, timeperiod=10)
    long_ema = talib.SMA(close, timeperiod=50)

    crossover = (short_ema > long_ema) & (np.roll(short_ema, 1) <= np.roll(long_ema, 1))
    crossunder = (short_ema < long_ema) & (np.roll(short_ema, 1) >= np.roll(long_ema, 1))
    signal = np.where(crossover, BUY_SIGNAL, NO_SIGNAL) + np.where(crossunder, SELL_SIGNAL, NO_SIGNAL)
    signal[0] = NO_SIGNAL

    return np.array([signal, close])



def order_fn(
    indicators: np.ndarray,
    index: int,
    params: TStrategyParams,
    pending_orders: TOrders,
) -> TOrderActions:
    signal = indicators[0]
    close = indicators[1]
    signal_at_index = signal[index]


    if signal_at_index == BUY_SIGNAL:
        return np.array([make_order_action_tuple(
            relative_size=0.,
            absolute_size=1.,
            stop_loss=0.,
            take_profit=0.,
            price=close[index] - 10,
            order_type=ORDER_TYPE__LIMIT,
            side=BUY_SIGNAL,
            user_id=0
        )], dtype=np.float64)
    elif signal_at_index == SELL_SIGNAL:
        return np.array([make_order_action_tuple(
            relative_size=0.,
            absolute_size=1.,
            stop_loss=0.,
            take_profit=0.,
            price=close[index] + 10,
            order_type=ORDER_TYPE__LIMIT,
            side=SELL_SIGNAL,
            user_id=0
        )], dtype=np.float64)
    else:
        return np.empty((0, 7), dtype=np.float64)



MyStrategy = Strategy(
    default_params=np.array([]),
    indicators_fn=indicators_fn,
    order_fn=order_fn
)



class LimitOrder(unittest.TestCase):
    ohlcv = get_ohlcv_data('crypto', 'BTC-USDT', '15min', "/Users/dyodio/Documents/Projects/Finance-Smash/backtester/tests/__data__")
    ohlcv = ohlcv[0:1500]
    begin_equity = 100_000_000_00

    backtest_strategy(
        strategy=MyStrategy,
        data=ohlcv,
        setup=(begin_equity, 0),
        params=np.array([])
    )

    start_time = time.time()

    result_info = backtest_strategy(
        strategy=MyStrategy,
        data=ohlcv,
        setup=(begin_equity, 0),
        params=np.array([])
    )

    end_time = time.time()

    time_taken = end_time - start_time

    final_equity = result_info[2]
    final_equity_rounded = round(final_equity, 2)

    print(f"Time taken: {time_taken} seconds")
    print(f"Final equity: {final_equity_rounded}")
    print(f"Final gain: {final_equity_rounded - begin_equity}")


    def test_result_is_expected(self):
        self.assertEqual(self.final_equity_rounded, 10000000328.34)
        # self.assertLess(self.time_taken, 0.0004)



if __name__ == '__main__':
    unittest.main()