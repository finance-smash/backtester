# from snapshottest import TestCase
# import pandas as pd
# import time
# from numba import njit
# import talib
# import numpy as np
# from tqdm import tqdm

# from backtester.commons import BUY_SIGNAL, NO_SIGNAL, SELL_SIGNAL, OHLCV__CLOSE,\
#     TOhlcv, ORDER_TYPE__LIMIT, OFFSET__CLOSE, OFFSET__OPEN, TSide, json_dumps_numpy
# from backtester.commons.helpers import get_ohlcv_data
# from backtester.order_action import TOrderActions, make_order_action_tuple 
# from backtester.position.position_type import POSITION__PL
# from backtester.strategy import TStrategyParams, cancel_pending_order_at_index
# from backtester.order import TOrders, ORDER__SIZE
# from backtester.position import TPositionTripleArray, POSITION__SIZE
# from backtester.strategy import backtest_strategy, grid_optimize
# from backtester.strategy.backtest_strategy import TBacktestResult, make_backtest_setup_tuple
# from backtester.strategy.grid_optimize_and_test_loop import grid_optimize_and_test_loop
# from backtester.strategy.strategy import Strategy
# from backtester.bt_result_plugin import with_fees

# COMMISSION_RATE = 0.00018
# with_fees_plugin = with_fees(COMMISSION_RATE)

# CLOSE = 0
# LONG_MA = 1
# SHORT_MA = 2
# BOLL_BANDS_UPPER = 3
# BOLL_BANDS_LOWER = 4
# PRICE_ABOVE_LONG_MA = 5
# PRICE_BELOW_LONG_MA = 6

# PARAMS__LONG_MA_LEN = 0
# PARAMS__SHORT_MA_LEN = 1
# PARAMS__BOLL_BAND_WIDTH = 2

# NB_OF_CANDLES_TO_OPTIMIZE_ON = 400000
# NB_OF_CANDLES_TO_TEST_ON = 200000
# NB_OF_CANDLES_FOR_STEP = 50000

# def indicators_fn(
#     data: TOhlcv,
#     params: TStrategyParams
# ) -> np.ndarray:
#     long_ma_len = params[PARAMS__LONG_MA_LEN]
#     short_ma_len = params[PARAMS__SHORT_MA_LEN]
#     bollinger_band_width = params[PARAMS__BOLL_BAND_WIDTH]

#     close = data[:, OHLCV__CLOSE]

#     long_ma = talib.SMA(close, timeperiod=long_ma_len)
#     short_ma = talib.SMA(close, timeperiod=short_ma_len)
#     boll_bands = talib.BBANDS(
#         close,
#         timeperiod=short_ma_len,
#         nbdevup=bollinger_band_width,
#         nbdevdn=bollinger_band_width,
#         matype=talib.MA_Type.SMA
#     )

#     boll_bands_upper = boll_bands[0]
#     boll_bands_lower = boll_bands[2]

#     price_above_long_ma = close > long_ma
#     price_below_long_ma = close < long_ma

#     ret = np.zeros((7, len(close)))

#     ret[CLOSE] = close
#     ret[LONG_MA] = long_ma
#     ret[SHORT_MA] = short_ma
#     ret[BOLL_BANDS_UPPER] = boll_bands_upper
#     ret[BOLL_BANDS_LOWER] = boll_bands_lower
#     ret[PRICE_ABOVE_LONG_MA] = price_above_long_ma
#     ret[PRICE_BELOW_LONG_MA] = price_below_long_ma

#     return ret


# def order_fn(
#     indicators: np.ndarray,
#     index: int,
#     params: TStrategyParams,
#     pending_orders: TOrders,
#     position_triple: TPositionTripleArray,
#     state: np.ndarray
# ) -> tuple[TOrderActions, np.ndarray]:
#     short_ma = indicators[SHORT_MA]
#     bollinger_bands_upper = indicators[BOLL_BANDS_UPPER]
#     bollinger_bands_lower = indicators[BOLL_BANDS_LOWER]
#     price_above_long_ma = indicators[PRICE_ABOVE_LONG_MA]
#     price_below_long_ma = indicators[PRICE_BELOW_LONG_MA]
#     close = indicators[CLOSE]

#     short_ma_at_index = short_ma[index]
#     bollinger_bands_upper_at_index = bollinger_bands_upper[index]
#     bollinger_bands_lower_at_index = bollinger_bands_lower[index]
#     price_above_long_ma_at_index = price_above_long_ma[index]
#     price_below_long_ma_at_index = price_below_long_ma[index]
#     close_at_index = close[index]

#     hedging_long_position = position_triple[1]
#     hedging_short_position = position_triple[2]

#     position_long_size = hedging_long_position[POSITION__SIZE]
#     position_short_size = hedging_short_position[POSITION__SIZE]

#     position_long_is_open = position_long_size != 0
#     position_short_is_open = position_short_size != 0

#     pending_order_len = len(pending_orders)

#     is_there_a_pending_order = False
#     for i in range(pending_order_len):
#         pending_order = pending_orders[i]
#         order_size = pending_order[ORDER__SIZE]
#         if not np.isnan(order_size):
#             is_there_a_pending_order = True
#             break

#     if is_there_a_pending_order:
#         for i in range(pending_order_len):
#             pending_order = pending_orders[i]
#             order_size = pending_order[ORDER__SIZE]
#             if not np.isnan(order_size):
#                 cancel_pending_order_at_index(
#                     pending_orders=pending_orders,
#                     pending_order_index=i
#                 )


#     order_actions = []


#     if position_long_is_open:
#         next_limit_close = max(short_ma_at_index, close_at_index + 1)
#         long_close_order_action = make_order_action_tuple(
#             relative_size=0.,
#             absolute_size=np.abs(position_long_size),
#             offset=OFFSET__CLOSE,
#             price=next_limit_close,
#             order_type=ORDER_TYPE__LIMIT,
#             side=SELL_SIGNAL,
#             user_id=0
#         )
#         order_actions.append(long_close_order_action)


#     if position_short_is_open:
#         next_limit_close = min(short_ma_at_index, close_at_index - 1)
#         short_close_order_action = make_order_action_tuple(
#             relative_size=0.,
#             absolute_size=np.abs(position_short_size),
#             offset=OFFSET__CLOSE,
#             price=next_limit_close,
#             order_type=ORDER_TYPE__LIMIT,
#             side=BUY_SIGNAL,
#             user_id=0
#         )
#         order_actions.append(short_close_order_action)


#     signal_at_index: TSide = NO_SIGNAL


#     if price_above_long_ma_at_index and close_at_index > bollinger_bands_lower_at_index:
#         signal_at_index = BUY_SIGNAL
#     elif price_below_long_ma_at_index and close_at_index < bollinger_bands_upper_at_index:
#         signal_at_index = SELL_SIGNAL


#     if signal_at_index == BUY_SIGNAL:
#         order_actions.append(make_order_action_tuple(
#             relative_size=0.,
#             absolute_size=1.,
#             take_profit=short_ma_at_index,
#             price=bollinger_bands_lower_at_index,
#             order_type=ORDER_TYPE__LIMIT,
#             side=BUY_SIGNAL,
#             offset=OFFSET__OPEN,
#             user_id=0
#         ))
#     elif signal_at_index == SELL_SIGNAL:
#         order_actions.append(make_order_action_tuple(
#             relative_size=0.,
#             absolute_size=1.,
#             take_profit=short_ma_at_index,
#             price=bollinger_bands_upper_at_index,
#             order_type=ORDER_TYPE__LIMIT,
#             side=SELL_SIGNAL,
#             offset=OFFSET__OPEN,
#             user_id=0
#         ))


#     np_arr_actions = np.array(order_actions, dtype=np.float64) if len(order_actions) > 0 else np.empty((0, 7), dtype=np.float64)

#     return (np_arr_actions, state)


# LimitMeanRevStrategy = Strategy(
#     default_params=np.array([200, 20, 2]),
#     indicators_fn=indicators_fn,
#     order_fn=order_fn
# )


# class TestWindowHardtestStrategy(TestCase):
    
#     def setUp(self):
#         self.data_len = 5000
#         optimize_indices, test_indices = generate_optimize_and_test_indices(
#             data_len=self.data_len,
#             nb_of_items_to_optimize_on=30,
#             nb_of_items_to_test_on=10,
#             nb_of_items_for_step=5
#         )
#         self.optimize_indices = optimize_indices
#         self.test_indices = test_indices
    
#     def test_basic_functionality(self):
#         """Test basic functionality and result integrity"""
#         self.assertEqual(len(self.optimize_indices), 994)
#         self.assertEqual(self.optimize_indices.shape, (994, 2))
#         self.assertEqual(len(self.test_indices), 994)
#         self.assertEqual(self.test_indices.shape, (994, 2))
    
#     def test_size_of_optimize_intervals_are_correct(self):
#         """Test that the size of the optimize intervals are correct"""
#         for optimize_index in self.optimize_indices:
#             self.assertEqual(optimize_index[1] - optimize_index[0], 30)

#     def test_size_of_test_intervals_are_correct(self):
#         """Test that the size of the test intervals are correct"""
#         for i in range(len(self.test_indices) - 1):
#             test_index = self.test_indices[i]
#             self.assertEqual(test_index[1] - test_index[0], 10)
#         last_test_index = self.test_indices[-1]
#         self.assertEqual(last_test_index[1] - last_test_index[0], 5)
    
#     def test_step_size_is_correct(self):
#         """Test that the step size is correct"""
#         for i in range(len(self.optimize_indices) - 1):
#             optimize_index = self.optimize_indices[i]
#             optimize_index_next = self.optimize_indices[i + 1]
#             self.assertEqual(optimize_index_next[0] - optimize_index[0], 5)


# if __name__ == '__main__':
#     unittest.main()