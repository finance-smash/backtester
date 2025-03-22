import unittest
import talib
import numpy as np
import time

from backtester.commons import get_ohlcv_data, BUY_SIGNAL, NO_SIGNAL, SELL_SIGNAL, OHLCV__CLOSE, TOhlcv, ORDER_TYPE__MARKET
from backtester.order_action import TOrderActions, make_order_action_tuple 
from backtester.strategy import Strategy, TStrategyParams, backtest_strategy
from backtester.order import TOrders
from backtester.position import POSITION__PL, TPositionTripleArray


def indicators_fn(data: TOhlcv, params: TStrategyParams) -> np.ndarray:
    close = data[:, OHLCV__CLOSE]
    short_ema = talib.SMA(data[:, OHLCV__CLOSE], timeperiod=10)
    long_ema = talib.SMA(data[:, OHLCV__CLOSE], timeperiod=50)

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
    position_triple: TPositionTripleArray,
    state: np.ndarray
) -> tuple[TOrderActions, np.ndarray]:
    signal = indicators[0]
    close = indicators[1]
    signal_at_index = signal[index]
    close_at_index = close[index]


    if signal_at_index == BUY_SIGNAL:
        return (np.array([make_order_action_tuple(
            relative_size=0.,
            absolute_size=1.,
            stop_loss=close_at_index - 10,
            order_type=ORDER_TYPE__MARKET,
            side=BUY_SIGNAL,
            user_id=0
        )], dtype=np.float64), state)
    elif signal_at_index == SELL_SIGNAL:
        return (np.array([make_order_action_tuple(
            relative_size=0.,
            absolute_size=1.,
            stop_loss=close_at_index + 10,
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



class WithSlFilledAtTheSameTimeOfEntry(unittest.TestCase):
    ohlcv = get_ohlcv_data('crypto', 'BTC-USDT', '15min', "/Users/dyodio/Documents/Projects/Finance-Smash/backtester/tests/__data__")
    ohlcv = ohlcv[0:1000]
    begin_equity = 100_000_000_00

    backtest_strategy(
        strategy=MyStrategy,
        data=ohlcv,
        setup=(begin_equity, 0, False),
        params=np.array([])
    )

    start_time = time.time()

    result_info = backtest_strategy(
        strategy=MyStrategy,
        data=ohlcv,
        setup=(begin_equity, 1, False),
        params=np.array([])
    )

    end_time = time.time()

    time_taken = end_time - start_time

    final_equity = result_info[2]
    final_equity_rounded = round(final_equity, 2)
    position_triple = result_info[0]

    pls_from_position_triple = np.nan_to_num(position_triple[:, POSITION__PL]).sum()
    final_gain_with_last_pls = pls_from_position_triple + final_equity - begin_equity
    final_gain_with_last_pls_rounded = round(final_gain_with_last_pls, 2)

    print(f"Time taken: {time_taken} seconds")
    print(f"Final equity: {final_equity_rounded}")
    print(f"Final gain: {final_equity - begin_equity}")
    print("Final gain with last pls:", final_gain_with_last_pls_rounded)

    def test_result_is_expected(self):
        self.assertEqual(self.final_gain_with_last_pls_rounded, -318.86)


if __name__ == '__main__':
    unittest.main()