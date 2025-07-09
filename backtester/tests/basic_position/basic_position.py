import unittest
import numpy as np

from backtester.commons import OHLCV__CLOSE, BUY_SIGNAL, SELL_SIGNAL, NO_SIGNAL
from backtester.indicators import ema_cross_signal
from backtester.order_action.make_order_action import market_order_for_signal
from backtester.strategy import Strategy
from backtester.tests.test_utils import run_and_assert



def indicators_fn(data, params):
    """Return only the ema_cross_signal for the close prices."""
    close = data[:, OHLCV__CLOSE]
    return np.array([ema_cross_signal(close)])


def order_fn(
    indicators,
    index: int,
    params,
    pending_orders,
    position_triple,
    state,
):
    signal_at_index = indicators[0][index]
    return (market_order_for_signal(signal_at_index, size=1.0), state)


MyStrategy = Strategy(
    default_params=np.array([]),
    indicators_fn=indicators_fn,
    order_fn=order_fn,
)


class BasicPosition(unittest.TestCase):
    def test_result_is_expected(self):
        run_and_assert(
            strategy=MyStrategy,
            ohlcv_path="backtester/tests/__data__",
            expected_equity=9999999917.07,
        )



if __name__ == "__main__":
    unittest.main()