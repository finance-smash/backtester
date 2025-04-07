import talib
import numpy as np

from backtester.commons import BUY_SIGNAL, NO_SIGNAL, SELL_SIGNAL, OHLCV__CLOSE,\
    TOhlcv, ORDER_TYPE__LIMIT, OFFSET__CLOSE, OFFSET__OPEN, TSide, json_dumps_numpy
from backtester.commons.helpers import get_ohlcv_data
from backtester.order_action import TOrderActions, make_order_action_tuple 
from backtester.position.position_type import POSITION__PL
from backtester.strategy import TStrategyParams, cancel_pending_order_at_index
from backtester.order import TOrders, ORDER__SIZE
from backtester.position import TPositionTripleArray, POSITION__SIZE
from backtester.strategy import backtest_strategy, grid_optimize
from backtester.strategy.backtest_strategy import make_backtest_setup_tuple
from backtester.strategy.grid_optimize_and_test_loop import grid_optimize_and_test_loop
from backtester.strategy.strategy import Strategy
from backtester.bt_result_plugin import with_fees

COMMISSION_RATE = 0.00018
with_fees_plugin = with_fees(COMMISSION_RATE)

CLOSE = 0
LONG_MA = 1
SHORT_MA = 2
BOLL_BANDS_UPPER = 3
BOLL_BANDS_LOWER = 4
PRICE_ABOVE_LONG_MA = 5
PRICE_BELOW_LONG_MA = 6

PARAMS__LONG_MA_LEN = 0
PARAMS__SHORT_MA_LEN = 1
PARAMS__BOLL_BAND_WIDTH = 2

def indicators_fn(
    data: TOhlcv,
    params: TStrategyParams
) -> np.ndarray:
    long_ma_len = params[PARAMS__LONG_MA_LEN]
    short_ma_len = params[PARAMS__SHORT_MA_LEN]
    bollinger_band_width = params[PARAMS__BOLL_BAND_WIDTH]

    close = data[:, OHLCV__CLOSE]

    long_ma = talib.SMA(close, timeperiod=long_ma_len)
    short_ma = talib.SMA(close, timeperiod=short_ma_len)
    boll_bands = talib.BBANDS(
        close,
        timeperiod=short_ma_len,
        nbdevup=bollinger_band_width,
        nbdevdn=bollinger_band_width,
        matype=talib.MA_Type.SMA
    )

    boll_bands_upper = boll_bands[0]
    boll_bands_lower = boll_bands[2]

    price_above_long_ma = close > long_ma
    price_below_long_ma = close < long_ma

    ret = np.zeros((7, len(close)))

    ret[CLOSE] = close
    ret[LONG_MA] = long_ma
    ret[SHORT_MA] = short_ma
    ret[BOLL_BANDS_UPPER] = boll_bands_upper
    ret[BOLL_BANDS_LOWER] = boll_bands_lower
    ret[PRICE_ABOVE_LONG_MA] = price_above_long_ma
    ret[PRICE_BELOW_LONG_MA] = price_below_long_ma

    return ret


def order_fn(
    indicators: np.ndarray,
    index: int,
    params: TStrategyParams,
    pending_orders: TOrders,
    position_triple: TPositionTripleArray,
    state: np.ndarray
) -> tuple[TOrderActions, np.ndarray]:
    short_ma = indicators[SHORT_MA]
    bollinger_bands_upper = indicators[BOLL_BANDS_UPPER]
    bollinger_bands_lower = indicators[BOLL_BANDS_LOWER]
    price_above_long_ma = indicators[PRICE_ABOVE_LONG_MA]
    price_below_long_ma = indicators[PRICE_BELOW_LONG_MA]
    close = indicators[CLOSE]

    short_ma_at_index = short_ma[index]
    bollinger_bands_upper_at_index = bollinger_bands_upper[index]
    bollinger_bands_lower_at_index = bollinger_bands_lower[index]
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


    if price_above_long_ma_at_index and close_at_index > bollinger_bands_lower_at_index:
        signal_at_index = BUY_SIGNAL
    elif price_below_long_ma_at_index and close_at_index < bollinger_bands_upper_at_index:
        signal_at_index = SELL_SIGNAL


    if signal_at_index == BUY_SIGNAL:
        order_actions.append(make_order_action_tuple(
            relative_size=0.,
            absolute_size=1.,
            take_profit=short_ma_at_index,
            price=bollinger_bands_lower_at_index,
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
            price=bollinger_bands_upper_at_index,
            order_type=ORDER_TYPE__LIMIT,
            side=SELL_SIGNAL,
            offset=OFFSET__OPEN,
            user_id=0
        ))


    np_arr_actions = np.array(order_actions, dtype=np.float64) if len(order_actions) > 0 else np.empty((0, 7), dtype=np.float64)

    if len(order_actions) > 0:
        state = np.concatenate((state, np.array([index])))

    return (np_arr_actions, state)


LimitMeanRevStrategy = Strategy(
    default_params=np.array([200, 20, 2]),
    indicators_fn=indicators_fn,
    order_fn=order_fn
)

ohlcv = get_ohlcv_data('crypto', 'BTC-USDT', '5min', "/Users/dyodio/Documents/Projects/Finance-Smash/backtester/tests/__data__")

# ohlcv = ohlcv[0:200000]
# ohlcv = ohlcv[0:200000]
begin_equity = 100_000_000_00

def maximize_fn(bt_result, params):
    all_pls = bt_result[3]
    all_sizes_abs = np.abs(all_pls[:, 2])
    total_size = all_sizes_abs.sum()
    pl_perc_mean = (all_pls[:, 1] * all_sizes_abs).sum() / total_size
    pl_perc_std = ((all_pls[:, 1] - pl_perc_mean)**2 * all_sizes_abs).sum() / total_size

    return (pl_perc_mean*100, np.array([pl_perc_std, len(all_pls)]))


def parse_bt_result(bt_result):
    all_pls_with_fees_res = with_fees_plugin(bt_result)
    all_pls_with_fees = all_pls_with_fees_res[:, 0]
    all_pls_pl_perc_with_fees = all_pls_with_fees_res[:, 1]

    final_equity = bt_result[2]
    final_equity_rounded = round(final_equity, 2)
    position_triple = bt_result[0]
    all_pls = bt_result[3]

    pls_from_position_triple = np.nan_to_num(position_triple[:, POSITION__PL]).sum()
    final_gain_with_last_pls = pls_from_position_triple + final_equity - begin_equity
    final_gain_with_last_pls_rounded = round(final_gain_with_last_pls, 2)


    all_sizes_abs = np.abs(all_pls[:, 2])
    total_size = all_sizes_abs.sum()
    pl_perc_mean = (all_pls[:, 1] * all_sizes_abs).sum() / total_size
    pl_perc_mean_with_fees = (all_pls_pl_perc_with_fees * all_sizes_abs).sum() / total_size

    return np.array([
        pl_perc_mean*100,
        pl_perc_mean_with_fees*100,
        final_equity_rounded,
        final_equity - begin_equity,
        len(all_pls),
        final_gain_with_last_pls_rounded
    ])

if __name__ == '__main__':

    backtest_setup = make_backtest_setup_tuple(
        begin_equity=begin_equity,
        is_hedged=1,
        auto_trigger_tp_sl=True
    )

    is_backtesting = True

    if is_backtesting:
        bt_result = backtest_strategy(
            strategy=LimitMeanRevStrategy,
            data=ohlcv,
            setup=backtest_setup,
            params=np.array([220, 75, 2.25]),
            state_shape=(0,)
        )

        all_pls_with_fees_res = with_fees_plugin(bt_result)
        all_pls_with_fees = all_pls_with_fees_res[:, 0]
        all_pls_pl_perc_with_fees = all_pls_with_fees_res[:, 1]
        state = bt_result[4]

        print(state)

        print(bt_result)


        final_equity = bt_result[2]
        final_equity_rounded = round(final_equity, 2)
        position_triple = bt_result[0]
        all_pls = bt_result[3]

        pls_from_position_triple = np.nan_to_num(position_triple[:, POSITION__PL]).sum()
        final_gain_with_last_pls = pls_from_position_triple + final_equity - begin_equity
        final_gain_with_last_pls_rounded = round(final_gain_with_last_pls, 2)

        print(all_pls)
        all_sizes_abs = np.abs(all_pls[:, 2])
        total_size = all_sizes_abs.sum()
        pl_perc_mean = (all_pls[:, 1] * all_sizes_abs).sum() / total_size
        pl_perc_mean_with_fees = (all_pls_pl_perc_with_fees * all_sizes_abs).sum() / total_size

        print(f"pl_perc_mean:", pl_perc_mean*100, "%")
        print(f"pl_perc_mean_with_fees:", pl_perc_mean_with_fees*100, "%")
        print(f"Final equity: {final_equity_rounded}")
        print(f"Final gain: {final_equity - begin_equity}")
        print(f"All pls length: {len(all_pls)}")
        print("Final gain with last pls:", final_gain_with_last_pls_rounded)

    all_params = [
        np.arange(100, 300, 10),
        np.arange(50, 100, 5),
        np.arange(2, 3, 0.25),
    ]
    # all_params = [
    #     np.arange(100, 150, 10),
    #     np.arange(10, 30, 5),
    #     np.arange(1, 1.5, 0.25),
    # ]

    is_loop_opti_testing = False

    if is_loop_opti_testing:
        loop_result = grid_optimize_and_test_loop(
            grid_optimization_setup=(
                all_params,
                0
            ),
            strategy=LimitMeanRevStrategy,
            data=ohlcv,
            backtest_setup=backtest_setup,
            maximize_fn=maximize_fn,
            nb_of_candles_to_optimize_on=350000,
            nb_of_candles_to_test_on=200000,
            nb_of_candles_for_step=100000,
            filter_possibility_fn=lambda params: params[PARAMS__LONG_MA_LEN] > params[PARAMS__SHORT_MA_LEN],
            nb_of_processes=4,
            parse_test_result_fn=parse_bt_result
        )

        print("loop_result")
        print(loop_result)

        json_dump_loop_result = json_dumps_numpy(loop_result)
        print("json_dump_loop_result")
        print(json_dump_loop_result, file=open("loop_result.json", "w"))



    is_optimizing = False

    if is_optimizing:
        # all_params = [
        #     np.arange(100, 150, 10),
        #     np.arange(10, 30, 5),
        #     np.arange(1, 1.5, 0.25),
        # ]

        # print("all_params")
        # print(all_params)

        grid_optim_result = grid_optimize(
            grid_optimization_setup=(
                all_params,
                0
            ),
            strategy=LimitMeanRevStrategy,
            data=ohlcv,
            backtest_setup=backtest_setup,
            maximize_fn=maximize_fn,
            filter_possibility_fn=lambda params: params[PARAMS__LONG_MA_LEN] > params[PARAMS__SHORT_MA_LEN],
            nb_of_processes=2
        )

        # print("grid_optim_result")
        # print(grid_optim_result)

        # nb_of_params = len(all_params)
        # print("nb_of_params")
        # print(nb_of_params)
        # best_params = grid_optim_result[0][1:nb_of_params+1]
        # print("best_params")
        # print(best_params)

        import pandas as pd

        # Create column names based on parameters and result
        columns = ['maximize_value', 'long_ma_len', 'short_ma_len', 'std_dev_mult', 'maximize_value_std']

        # Convert to DataFrame and save to CSV
        pd.DataFrame(grid_optim_result, columns=columns).to_csv('grid_optimization_results.csv', index=False)
    

