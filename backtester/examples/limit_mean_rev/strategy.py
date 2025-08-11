import os
import pandas as pd
import time
from numba import njit
import talib
import numpy as np
from tqdm import tqdm
from datetime import datetime, timedelta

from backtester.commons import BUY_SIGNAL, NO_SIGNAL, SELL_SIGNAL, OHLCV__CLOSE,\
    TOhlcv, ORDER_TYPE__LIMIT, OFFSET__CLOSE, OFFSET__OPEN, TSide, json_dumps_numpy
from backtester.commons.helpers import get_ohlcv_data
from backtester.order_action import TOrderActions, make_order_action_tuple 
from backtester.position.position_type import POSITION__PL
from backtester.strategy import TStrategyParams, cancel_pending_order_at_index
from backtester.order import TOrders, ORDER__SIZE
from backtester.position import TPositionTripleArray, POSITION__SIZE
from backtester.strategy import backtest_strategy, grid_optimize
from backtester.strategy.backtest_strategy import TBacktestResult, get_begin_at_index, make_backtest_setup_tuple
from backtester.strategy.grid_optimize_and_test_loop import grid_optimize_and_test_loop
from backtester.strategy.strategy import Strategy
from backtester.bt_result_plugin import with_fees
from backtester.strategy.window_hardtest_strategy.window_hardtest_strategy import window_hardtest_strategy_inner

COMMISSION_RATE = 0.00018
with_fees_plugin = with_fees(COMMISSION_RATE)

def get_number_of_decimals(x: float):
    splitted = str(x).split('.')
    if len(splitted) <= 1:
        return 0
    return len(splitted[1])

def get_pip_size(prices: np.ndarray):
    max_number_of_decimals = np.array([get_number_of_decimals(x) for x in prices]).max()
    return 10.0 ** (-max_number_of_decimals)

def safe_div(a, b):
    if b == 0:
        return np.nan
    return a / b

CLOSE = 0
LONG_MA = 1
SHORT_MA = 2
BOLL_BANDS_UPPER = 3
BOLL_BANDS_LOWER = 4
PRICE_ABOVE_LONG_MA = 5
PRICE_BELOW_LONG_MA = 6
PIP_SIZE = 7

PARAMS__LONG_MA_LEN = 0
PARAMS__SHORT_MA_LEN = 1
PARAMS__BOLL_BAND_WIDTH = 2

NB_OF_CANDLES_TO_OPTIMIZE_ON = 400000
NB_OF_CANDLES_TO_TEST_ON = 200000
NB_OF_CANDLES_FOR_STEP = 50000

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

    ret = np.zeros((8, len(close)))

    ret[CLOSE] = close
    ret[LONG_MA] = long_ma
    ret[SHORT_MA] = short_ma
    ret[BOLL_BANDS_UPPER] = boll_bands_upper
    ret[BOLL_BANDS_LOWER] = boll_bands_lower
    ret[PRICE_ABOVE_LONG_MA] = price_above_long_ma
    ret[PRICE_BELOW_LONG_MA] = price_below_long_ma

    pip_size = get_pip_size(close)
    ret[PIP_SIZE] = pip_size

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
    pip_size = indicators[PIP_SIZE][0]

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
        next_limit_close = max(short_ma_at_index, close_at_index + pip_size)
        if next_limit_close > 0:
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
        next_limit_close = min(short_ma_at_index, close_at_index - pip_size)
        if next_limit_close > 0:
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
        if bollinger_bands_lower_at_index > 0:
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
        if bollinger_bands_upper_at_index > 0:
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

    # if len(order_actions) > 0:
    #     state = np.concatenate((state, np.array([index]))) #NOTE this increases the time taken by A LOOOOOT find another way to do this

    return (np_arr_actions, state)


LimitMeanRevStrategy = Strategy(
    default_params=np.array([200, 20, 2]),
    indicators_fn=indicators_fn,
    order_fn=order_fn
)
crypto = 'ETH-USDT'
ohlcv, _ = get_ohlcv_data('crypto', crypto, '5min', "/Users/dyodio/Documents/Projects/Finance-Smash/data")

# ohlcv = ohlcv[0:200000]
# ohlcv = ohlcv[0:200000]
begin_equity = 100_000_000_00

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


@njit
def maximize_fn(results_list: list[tuple[TBacktestResult, TStrategyParams]]):
    (bt_result, params) = results_list[0]
    all_pls = bt_result[3]
    all_sizes_abs = np.abs(all_pls[:, 2])
    total_size = all_sizes_abs.sum()
    pl_perc_mean = (all_pls[:, 1] * all_sizes_abs).sum() / total_size

    ret = (pl_perc_mean*100, np.array([len(all_pls)]))
    return ret

@njit
def maximize_fn2(results_list: list[tuple[TBacktestResult, TStrategyParams]]):
    pl_perc_means = np.zeros(len(results_list))
    all_pls_lenghts = np.zeros(len(results_list))
    for i, (bt_result, params) in enumerate(results_list):
        all_pls = bt_result[3]
        all_sizes_abs = np.abs(all_pls[:, 2])
        total_size = all_sizes_abs.sum()
        if total_size == 0:
            pl_perc_mean = 0
        else:
            pl_perc_mean = (all_pls[:, 1] * all_sizes_abs).sum() / (total_size)
        pl_perc_means[i] = pl_perc_mean*100
        all_pls_lenghts[i] = len(all_pls)


    concat_len_and_pl_perc_means = np.concatenate((all_pls_lenghts, pl_perc_means))
    return (pl_perc_means.mean(), concat_len_and_pl_perc_means)


if __name__ == '__main__':

    backtest_setup = make_backtest_setup_tuple(
        begin_equity=begin_equity,
        is_hedged=1,
        auto_trigger_tp_sl=True
    )

    is_backtesting = False

    if is_backtesting:
        bt_result = backtest_strategy(
            strategy=LimitMeanRevStrategy,
            data=ohlcv[0:1000],
            setup=backtest_setup,
            params=np.array([220,90,2.75]),
        )

        begin_time = time.time()

        bt_result = backtest_strategy(
            strategy=LimitMeanRevStrategy,
            data=ohlcv[200000*2:200000*3],
            setup=backtest_setup,
            params=np.array([220,90,2.75]),
        )

        end_time = time.time()
        print(f"Time taken: {end_time - begin_time} seconds")

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
    #     np.arange(100, 120, 10),
    #     np.arange(10, 20, 5),
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
            nb_of_candles_to_optimize_on=NB_OF_CANDLES_TO_OPTIMIZE_ON,
            nb_of_candles_to_test_on=NB_OF_CANDLES_TO_TEST_ON,
            nb_of_candles_for_step=NB_OF_CANDLES_FOR_STEP,
            filter_possibility_fn=lambda params: params[PARAMS__LONG_MA_LEN] > params[PARAMS__SHORT_MA_LEN],
            nb_of_processes=4,
            parse_test_result_fn=parse_bt_result
        )

        print("loop_result")
        print(loop_result)

        json_dump_loop_result = json_dumps_numpy(loop_result)
        print("json_dump_loop_result")
        print(json_dump_loop_result, file=open("loop_result.json", "w"))


    N = 20000
    number_of_data_chunks = 10
    first_data_chunk_index = 1

    is_optimizing = False

    if is_optimizing:
        # all_params = [
        #     np.arange(100, 150, 10),
        #     np.arange(10, 30, 5),
        #     np.arange(1, 1.5, 0.25),
        # ]

        # print("all_params")
        # print(all_params)

        data = [ohlcv[(i + first_data_chunk_index)*N:(i+1+first_data_chunk_index)*N] for i in range(number_of_data_chunks)]

        grid_optim_result = grid_optimize(
            grid_optimization_setup=(
                all_params,
                0
            ),
            strategy=LimitMeanRevStrategy,
            data=data,
            backtest_setup=backtest_setup,
            maximize_fn=maximize_fn2,
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

        # Create column names based on parameters and result
        pl_len_cols = [f'pl_len_{i}' for i in range(number_of_data_chunks)]
        pl_perc_cols = [f'pl_perc_{i}' for i in range(number_of_data_chunks)]
        columns = ['maximize_value', 'long_ma_len', 'short_ma_len', 'std_dev_mult'] + pl_len_cols + pl_perc_cols

        print("grid_optim_result")
        print(grid_optim_result)

        # Convert to DataFrame and save to CSV
        pd.DataFrame(grid_optim_result, columns=columns).to_csv(
            f'grid_optimization_results_{first_data_chunk_index}_{crypto}.csv', index=False
        )

    
    if_backtesting_on_opti_result = False

    if if_backtesting_on_opti_result:
        grid_optim_result = pd.read_csv(f'grid_optimization_results_{first_data_chunk_index}_{crypto}.csv')
        print("grid_optim_result")
        print(grid_optim_result)

        new_csv_data = []

        print('N*(number_of_data_chunks + first_data_chunk_index)')
        print(N*(number_of_data_chunks + first_data_chunk_index))
        print('N*(number_of_data_chunks+1+first_data_chunk_index)')
        print(N*(number_of_data_chunks+1+first_data_chunk_index))

        test_ohlcv = ohlcv[N*(number_of_data_chunks + first_data_chunk_index):N*(number_of_data_chunks+1+first_data_chunk_index)]
        print('test_ohlcv[0]')
        print(test_ohlcv[0])
        print('test_ohlcv[1]')
        print(test_ohlcv[1])

        re_optim = grid_optimize(
            grid_optimization_setup=(
                all_params,
                0
            ),
            strategy=LimitMeanRevStrategy,
            data=[test_ohlcv],
            backtest_setup=backtest_setup,
            maximize_fn=maximize_fn2,
            filter_possibility_fn=lambda params: params[PARAMS__LONG_MA_LEN] > params[PARAMS__SHORT_MA_LEN],
            nb_of_processes=2
        )

        columns = ['maximize_value', 'long_ma_len', 'short_ma_len', 'std_dev_mult'] + ['pl_test_len', 'pl_test_mean_perc']
        # Convert to DataFrame and save to CSV
        pd.DataFrame(re_optim, columns=columns).to_csv(
            f'grid_optimization_results_{first_data_chunk_index}_{crypto}_with_reopt.csv', index=False
        )

        for optim_result in tqdm(grid_optim_result.itertuples()):
            optim_result = optim_result[1:]
            optim_result_params = optim_result[1:4]
            bt_result = backtest_strategy(
                strategy=LimitMeanRevStrategy,
                data=test_ohlcv,
                setup=backtest_setup,
                params=optim_result_params,
            )
            all_pls = bt_result[3]
            all_sizes_abs = np.abs(all_pls[:, 2])
            total_size = all_sizes_abs.sum()
            pl_perc_mean = (all_pls[:, 1] * all_sizes_abs).sum() / total_size

            new_csv_data.append(optim_result + (pl_perc_mean*100,))

        new_columns = grid_optim_result.columns.tolist() + ['pl_perc_mean_test']
        
        print('new_col len', len(new_columns))

        
        pd.DataFrame(new_csv_data, columns=new_columns).to_csv(
            f'grid_optimization_results_{first_data_chunk_index}_2_{crypto}.csv', index=False
        )
    


    cryptos = [
        'ADA-USDT',
        'AGIX-USDT',
        'APT-USDT',
        'ARB-USDT',
        'ATOM-USDT',
        'AVAX-USDT',
        'AXS-USDT',
        'BCH-USDT',
        'BEAM-USDT',
        'BNB-USDT',
        'BTC-USDT',
        'BTT-USDT',
        'CFX-USDT',
        'CHZ-USDT',
        'DAI-USDT',
        'DOGE-USDT',
        'DOT-USDT',
        'DYDX-USDT',
        'EGLD-USDT',
        'ENA-USDT',
        'ENS-USDT',
        'EOS-USDT',
        'ETC-USDT',
        'ETH-USDT',
        'GALA-USDT',
        'GNO-USDT',
        'HBAR-USDT',
        'ICP-USDT',
        'LINK-USDT',
        'LTC-USDT',
        'MATIC-USDT',
        'NEAR-USDT',
        'NEO-USDT',
        'NEXO-USDT',
        'ORDI-USDT',
        'PENDLE-USDT',
        'PEPE-USDT',
        'QNT-USDT',
        'RNDR-USDT',
        'SAND-USDT',
        'SHIB-USDT',
        'SNX-USDT',
        'SOL-USDT',
        'TON-USDT',
        'TRX-USDT',
        'UNI-USDT',
        'WLD-USDT',
        'XLM-USDT',
        'XMR-USDT',
        'XRP-USDT',
        'XTZ-USDT',
        'ZRO-USDT',
    ]
    crypto_ohlcv_dict = {c: get_ohlcv_data('crypto', c, '5min', "/Users/dyodio/Documents/Projects/Finance-Smash/data") for c in cryptos}
    window_size = 30000
    begin_at_index = 48000
    crypto_nb_of_optimization_windows_dict = {c: (len(crypto_ohlcv_dict[c][0]) - begin_at_index) // window_size for c in cryptos}

    is_window_hardtest = False
    if is_window_hardtest:
        all_params = [
            np.arange(24000, 48000, 1000),
            np.arange(20, 100, 5),
            np.arange(2, 3, 0.25),
        ]

        for c in cryptos:
            file_name = f'window_hardtest_results_{c}.csv'
            file_already_exists = os.path.exists(file_name)
            nb_of_optimization_windows = crypto_nb_of_optimization_windows_dict[c]

            if nb_of_optimization_windows <= 1:
                print('nb_of_optimization_windows <= 1 for', c, "ignoring")
                continue

            if file_already_exists:
                continue

            ohlcv_data, _ = crypto_ohlcv_dict[c]
            print('ohlcv length for', c)
            print(len(ohlcv_data))

            print('nb_of_optimization_windows for', c)
            print(nb_of_optimization_windows)

            pl_len_cols = [f'pl_len_{i}' for i in range(nb_of_optimization_windows)]
            pl_perc_cols = [f'pl_perc_{i}' for i in range(nb_of_optimization_windows)]
            columns = ['maximize_value', 'long_ma_len', 'short_ma_len', 'std_dev_mult'] + pl_len_cols + pl_perc_cols
            new_columns = columns + ['pl_test_min', 'pl_test_len', 'pl_test_mean_perc']

            df = window_hardtest_strategy_inner(
                ohlcv=ohlcv_data,
                optimization_window=window_size,
                nb_of_optimization_windows=nb_of_optimization_windows,
                test_window=window_size,
                maximize_fn=maximize_fn2,
                strategy=LimitMeanRevStrategy,
                backtest_setup=backtest_setup,
                grid_optimization_setup=(
                    all_params,
                    0
                ),
                final_csv_column_names=new_columns,
                filter_possibility_fn=lambda params: params[PARAMS__LONG_MA_LEN] > params[PARAMS__SHORT_MA_LEN],
                nb_of_test_windows=1,
                first_optimization_window_index=0,
                nb_of_processes=8,
                begin_at_index=begin_at_index,
            )

            df.to_csv(file_name, index=False)


    is_analyzing_window_hardtest = True
    if is_analyzing_window_hardtest:

        for crypto in cryptos:
            nb_of_optimization_windows = crypto_nb_of_optimization_windows_dict[crypto]
            how_many_windows_to_analyze = 1
            try:
                df = pd.read_csv(f'window_hardtest_results_{crypto}.csv', nrows=10)
            except:
                print('file not found for', crypto)
                continue

            nb_of_items_analyzed = 0
            nb_of_items_positive_analyzed = 0
            nb_of_items_negative_analyzed = 0

            avg_pl_sum = 0
            avg_pl_if_positive_sum = 0
            avg_pl_if_negative_sum = 0

            for index, row  in df.iterrows():
                for j in range(how_many_windows_to_analyze, nb_of_optimization_windows):
                    pl_perc_curr = row[f'pl_perc_{j}']
                    pl_len_curr = row[f'pl_len_{j}']

                    if pl_len_curr == 0:
                        continue

                    pl_perc_all_mean = 0
                    pl_perc_all_len = 0
                    for i in range(j - how_many_windows_to_analyze, j):
                        pl_perc_mean = row[f'pl_perc_{i}']
                        pl_perc_len = row[f'pl_len_{i}']
                        pl_perc_all_mean += (pl_perc_mean * pl_perc_len)
                        pl_perc_all_len += pl_perc_len
                    
                    if pl_perc_all_len == 0:
                        continue

                    nb_of_items_analyzed += 1
                    avg_pl_sum += pl_perc_curr
                    
                    if pl_perc_all_mean > 0:
                        nb_of_items_positive_analyzed += 1
                        avg_pl_if_positive_sum += pl_perc_curr
                    else:
                        nb_of_items_negative_analyzed += 1
                        avg_pl_if_negative_sum += pl_perc_curr


            avg_pl = safe_div(avg_pl_sum, nb_of_items_analyzed)
            avg_pl_if_positive = safe_div(avg_pl_if_positive_sum, nb_of_items_positive_analyzed)
            avg_pl_if_negative = safe_div(avg_pl_if_negative_sum, nb_of_items_negative_analyzed)

            print('-'*30)
            print('-'*30)
            print('crypto')
            print(crypto)
            print('-'*30)
            print('nb_of_optimization_windows')
            print(nb_of_optimization_windows)
            print('-'*30)
            print('how_many_windows_to_analyze')
            print(how_many_windows_to_analyze)
            print('-'*30)
            print('nb_of_items_analyzed')
            print(nb_of_items_analyzed)
            print('avg_pl')
            print(avg_pl, '%')
            print('-'*30)
            print('nb_of_items_positive_analyzed')
            print(nb_of_items_positive_analyzed)
            print('avg_pl_if_positive')
            print(avg_pl_if_positive, '%')
            print('-'*30)
            print('nb_of_items_negative_analyzed')
            print(nb_of_items_negative_analyzed)
            print('avg_pl_if_negative')
            print(avg_pl_if_negative, '%')
            print('-'*30)



    is_testing_link_crypto = False
    if is_testing_link_crypto:
        crypto = 'LINK-USDT'
        ohlcv, ohlcv_gmt_times = crypto_ohlcv_dict[crypto]
        data = ohlcv[0:window_size + 48000]
        print('data')
        print(data[0], data[-1])

        bt_result = backtest_strategy(
            strategy=LimitMeanRevStrategy,
            data=ohlcv[0:10000],
            setup=backtest_setup,
            params=np.array([31000.0,35.0,2.25]),
            begin_at_index=48000
        )

        time_start = time.time()

        bt_result = backtest_strategy(
            strategy=LimitMeanRevStrategy,
            data=ohlcv[0:window_size + 48000],
            setup=backtest_setup,
            params=np.array([31000.0,35.0,2.25]),
            begin_at_index=48000
        )

        time_end = time.time()
        print('time taken', (time_end - time_start) * 1000, 'ms')

        all_pls = bt_result[3]
        print('all_pls')
        print(all_pls)
        print(len(all_pls))
        all_sizes_abs = np.abs(all_pls[:, 2])
        total_size = all_sizes_abs.sum()
        pl_perc_mean = (all_pls[:, 1] * all_sizes_abs).sum() / total_size

        print('pl_perc_mean')
        print(pl_perc_mean * 100)
        