import unittest
import talib
import numpy as np
import time

from backtester.commons import get_ohlcv_data, BUY_SIGNAL, NO_SIGNAL, SELL_SIGNAL, OHLCV__CLOSE, TOhlcv, ORDER_TYPE__MARKET
from backtester.order import TOrders
from backtester.order_action import TOrderActions, make_order_action_tuple 
from backtester.strategy import Strategy, TStrategyParams, backtest_strategy, grid_optimize
from backtester.position import TPositionTripleArray


def indicators_fn(data: TOhlcv, params: TStrategyParams) -> np.ndarray:
    short_ema_timeperiod = params[0]
    long_ema_timeperiod = params[1]

    short_ema = talib.SMA(data[:, OHLCV__CLOSE], timeperiod=short_ema_timeperiod)
    long_ema = talib.SMA(data[:, OHLCV__CLOSE], timeperiod=long_ema_timeperiod)

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

def get_final_equity_from_grid_optimize_result(grid_optimize_result):
    return grid_optimize_result[0][0][2]

class BasicPositionGridOptimize(unittest.TestCase):
    ohlcv , _ = get_ohlcv_data('crypto', 'BTC-USDT', '15min', "/Users/dyodio/Documents/Projects/Finance-Smash/backtester/tests/__data__")
    ohlcv = ohlcv[0:1500]
    begin_equity = 100_000_000_00

    grid_optimize(
        grid_optimization_setup=(
            [np.array([10]), np.array([50])],
            0
        ),
        strategy=MyStrategy,
        data=[ohlcv],
        backtest_setup=(begin_equity, 0, False, False),
        maximize_fn=lambda x: (
            get_final_equity_from_grid_optimize_result(x),
            []
        )
    )

    start_time = time.time()

    grid_optimize_result = grid_optimize(
        grid_optimization_setup=(
            np.array([[10, 20, 30], [50, 60, 70]]),
            0
        ),
        strategy=MyStrategy,
        data=[ohlcv],
        backtest_setup=(begin_equity, 0, False, False),
        maximize_fn=lambda x: (
            get_final_equity_from_grid_optimize_result(x),
            np.array([1, 2])
        )
    )

    np.set_printoptions(formatter={'all':lambda x: str(x)})

    expected_results = np.array([
        [10000000272.67, 10.0, 70.0, 1.0, 2.0],
        [10000000226.259998, 10.0, 60.0, 1.0, 2.0],
        [10000000178.8, 30.0, 70.0, 1.0, 2.0],
        [10000000073.099997, 20.0, 70.0, 1.0, 2.0],
        [10000000038.63, 30.0, 60.0, 1.0, 2.0],
        [9999999917.07, 10.0, 50.0, 1.0, 2.0],
        [9999999889.2, 30.0, 50.0, 1.0, 2.0],
        [9999999760.670004, 20.0, 60.0, 1.0, 2.0],
        [9999999717.699999, 20.0, 50.0, 1.0, 2.0]
    ])

    grid_optimize_result_with_filter = grid_optimize(
        grid_optimization_setup=(
            np.array([[10, 20, 30], [50, 60, 70]]),
            0
        ),
        strategy=MyStrategy,
        data=[ohlcv],
        backtest_setup=(begin_equity, 0, False, False),
        maximize_fn=lambda x: (
            get_final_equity_from_grid_optimize_result(x),
            np.array([1, 2])
        ),
        filter_possibility_fn=lambda params: params[0] != 20
    )

    expected_results_with_filter = np.array([
        [10000000272.67, 10.0, 70.0, 1.0, 2.0],
        [10000000226.259998, 10.0, 60.0, 1.0, 2.0],
        [10000000178.8, 30.0, 70.0, 1.0, 2.0],
        [10000000038.63, 30.0, 60.0, 1.0, 2.0],
        [9999999917.07, 10.0, 50.0, 1.0, 2.0],
        [9999999889.2, 30.0, 50.0, 1.0, 2.0],
    ])

    grid_optimize_result_with_max_tries = grid_optimize(
        grid_optimization_setup=(
            np.array([[10, 20, 30], [50, 60, 70]]),
            3
        ),
        strategy=MyStrategy,
        data=[ohlcv],
        backtest_setup=(begin_equity, 0, False, False),
        maximize_fn=lambda x: (
            get_final_equity_from_grid_optimize_result(x),
            np.array([1, 2])
        )
    )

    expected_results_with_max_tries = np.array([
        [10000000272.67, 10.0, 70.0, 1.0, 2.0],
        [10000000226.259998, 10.0, 60.0, 1.0, 2.0],
        [9999999917.07, 10.0, 50.0, 1.0, 2.0],
    ])


    end_time = time.time()

    time_taken = end_time - start_time

    print(f"Time taken: {time_taken} seconds")

    def test_result_is_expected(self):
        np.testing.assert_array_equal(self.grid_optimize_result, self.expected_results)
        np.testing.assert_array_equal(self.grid_optimize_result_with_filter, self.expected_results_with_filter)
        np.testing.assert_array_equal(self.grid_optimize_result_with_max_tries, self.expected_results_with_max_tries)



if __name__ == '__main__':
    unittest.main()
