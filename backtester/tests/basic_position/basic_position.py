import unittest
import talib
import numpy as np
import time

from backtester.commons import get_ohlcv_data, BUY_SIGNAL, NO_SIGNAL, SELL_SIGNAL, OHLCV__CLOSE, TOhlcv, ORDER_TYPE__MARKET
from backtester.order import TOrders
from backtester.order_action import TOrderActions, make_order_action_tuple 
from backtester.strategy import Strategy, TStrategyParams, backtest_strategy
from backtester.position import TPositionTripleArray
from backtester.bt_result_plugin import with_fees

COMMISSION_RATE = 0.00018
with_fees_plugin = with_fees(COMMISSION_RATE)

def indicators_fn(data: TOhlcv, params: TStrategyParams) -> np.ndarray:
    short_ema = talib.SMA(data[:, OHLCV__CLOSE], timeperiod=10)
    long_ema = talib.SMA(data[:, OHLCV__CLOSE], timeperiod=50)

    crossover = (short_ema > long_ema) & (np.roll(short_ema, 1) <= np.roll(long_ema, 1))
    crossunder = (short_ema < long_ema) & (np.roll(short_ema, 1) >= np.roll(long_ema, 1))
    signal = np.where(crossover, BUY_SIGNAL, NO_SIGNAL) + np.where(crossunder, SELL_SIGNAL, NO_SIGNAL)
    signal[0] = NO_SIGNAL

    return np.array([signal])



def order_fn(
        indicators: np.ndarray,
        index: int,
        params: TStrategyParams,
        pending_orders: TOrders,
        position_triple: TPositionTripleArray,
        state: np.ndarray
    ) -> tuple[TOrderActions, np.ndarray]:
    signal = indicators[0]
    signal_at_index = signal[index]


    if signal_at_index == BUY_SIGNAL:
        return (np.array([make_order_action_tuple(
            relative_size=0.,
            absolute_size=1.,
            stop_loss=0.,
            take_profit=0.,
            order_type=ORDER_TYPE__MARKET,
            side=BUY_SIGNAL,
            user_id=0
        )], dtype=np.float64), state)
    elif signal_at_index == SELL_SIGNAL:
        return (np.array([make_order_action_tuple(
            relative_size=0.,
            absolute_size=1.,
            stop_loss=0.,
            take_profit=0.,
            order_type=ORDER_TYPE__MARKET,
            side=SELL_SIGNAL,
            user_id=0
        )], dtype=np.float64), state)
    else:
        return (np.empty((0, 7), dtype=np.float64), state)



MyStrategy = Strategy(
    default_params=np.array([]),
    indicators_fn=indicators_fn,
    order_fn=order_fn
)



class BasicPosition(unittest.TestCase):
    ohlcv , _ = get_ohlcv_data('crypto', 'BTC-USDT', '15min', "/Users/dyodio/Documents/Projects/Finance-Smash/backtester/tests/__data__")
    ohlcv = ohlcv[0:1500]
    begin_equity = 100_000_000_00

    backtest_strategy(
        strategy=MyStrategy,
        data=ohlcv,
        setup=(begin_equity, 0, False, False),
        params=np.array([])
    )

    start_time = time.time()

    result_info = backtest_strategy(
        strategy=MyStrategy,
        data=ohlcv,
        setup=(begin_equity, 0, False, True),
        params=np.array([])
    )

    end_time = time.time()

    all_pls_with_fees_res = with_fees_plugin(result_info)
    print(all_pls_with_fees_res)
    all_pls_with_fees = all_pls_with_fees_res[:, 0]
    all_pls_with_fees_sum = round(np.sum(all_pls_with_fees), 3)

    all_pls = result_info[3]
    all_pls_pl = all_pls[:, 0]
    all_pls_sum = round(np.sum(all_pls_pl), 3)
    order_history = result_info[5]
    print(order_history)

    fees = np.abs(round(all_pls_with_fees_sum - all_pls_sum, 3))

    time_taken = end_time - start_time
    final_equity = result_info[2]
    final_equity_rounded = round(final_equity, 2)
    final_equity_with_fees = round(final_equity - fees, 2)

    print(f"Time taken: {time_taken} seconds")
    print(f"Final equity: {final_equity_rounded}")
    print(f"Final equity with fees: {final_equity_with_fees}")
    print(f"Final gain: {final_equity - begin_equity}")
    print(f"Final gain with fees: {final_equity_with_fees - begin_equity}")


    def test_result_is_expected(self):
        self.assertEqual(self.final_equity_rounded, 9999999917.07)
        self.assertEqual(self.final_equity_with_fees, 9999999885.8)
        self.assertEqual(self.all_pls_with_fees_sum, -114.205)
        self.assertEqual(self.all_pls_sum, -82.93)
        self.assertEqual(self.fees, 31.275)


if __name__ == '__main__':
    unittest.main()