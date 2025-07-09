import unittest
import numpy as np

from backtester.commons import OHLCV__CLOSE, BUY_SIGNAL, SELL_SIGNAL, ORDER_TYPE__LIMIT
from backtester.indicators import ema_cross_signal
from backtester.order_action.make_order_action import market_order_for_signal
from backtester.strategy import Strategy
from backtester.tests.test_utils import run_and_assert


def indicators_fn(data, params):
    close = data[:, OHLCV__CLOSE]
    return np.array([ema_cross_signal(close), close])


def order_fn(
    indicators,
    index: int,
    params,
    pending_orders,
    position_triple,
    state,
):
    signal_at_index = indicators[0][index]
    close_at_index = indicators[1][index]

    if signal_at_index == BUY_SIGNAL:
        order = market_order_for_signal(
            signal_at_index,
            size=1.0,
            price=close_at_index - 10,
            order_type=ORDER_TYPE__LIMIT,
        )
    elif signal_at_index == SELL_SIGNAL:
        order = market_order_for_signal(
            signal_at_index,
            size=1.0,
            price=close_at_index + 10,
            order_type=ORDER_TYPE__LIMIT,
        )
    else:
        order = market_order_for_signal(signal_at_index)

    return (order, state)


MyStrategy = Strategy(
    default_params=np.array([]),
    indicators_fn=indicators_fn,
    order_fn=order_fn,
)



class LimitOrder(unittest.TestCase):
    def test_result_is_expected(self):
        run_and_assert(
            strategy=MyStrategy,
            ohlcv_path="backtester/tests/__data__",
            expected_equity=10000000328.34,
        )



if __name__ == "__main__":
    unittest.main()