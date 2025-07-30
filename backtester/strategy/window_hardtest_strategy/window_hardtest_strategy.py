from typing import Callable
from backtester.commons.ohlcv_type import TOhlcv
from backtester.strategy.optimize_strategy_grid import TFilterPossibilityFn, TGridOptimizationSetupTuple, TMaximizeFn,\
    grid_optimize
from backtester.strategy.strategy import Strategy, TBacktestSetup
import pandas as pd
import numpy as np


def window_hardtest_strategy_inner(
    ohlcv: TOhlcv,
    optimization_window: int,
    nb_of_optimization_windows: int,
    test_window: int,
    maximize_fn: TMaximizeFn,
    strategy: Strategy,
    backtest_setup: TBacktestSetup,
    grid_optimization_setup: TGridOptimizationSetupTuple,
    final_csv_column_names: list[str],
    filter_possibility_fn: TFilterPossibilityFn = None,
    nb_of_test_windows: int = 1,
    first_optimization_window_index: int = 0,
    nb_of_processes: int = 1,
    begin_at_index: int = 0
):
    W = optimization_window
    NW = nb_of_optimization_windows
    F = first_optimization_window_index

    optimization_ohlcvs = [ohlcv[(i + F)*W:(i+1+F)*W + begin_at_index] for i in range(NW)]

    grid_optim_result = grid_optimize(
        grid_optimization_setup=grid_optimization_setup,
        strategy=strategy,
        data=optimization_ohlcvs,
        backtest_setup=backtest_setup,
        maximize_fn=maximize_fn,
        filter_possibility_fn=filter_possibility_fn,
        nb_of_processes=nb_of_processes,
        begin_at_index=begin_at_index
    )

    TW = test_window
    TNW = nb_of_test_windows

    nb_of_params = len(strategy.default_params)

    last_optimization_window_index = (NW + F) * W

    test_ohlcv = [ohlcv[
        last_optimization_window_index + i*TW:
        last_optimization_window_index + (i+1)*TW + begin_at_index
    ] for i in range(TNW)]

    grid_optim_result_on_test = grid_optimize(
        grid_optimization_setup=grid_optimization_setup,
        strategy=strategy,
        data=test_ohlcv,
        backtest_setup=backtest_setup,
        maximize_fn=maximize_fn,
        filter_possibility_fn=filter_possibility_fn,
        nb_of_processes=nb_of_processes
    )

    aggregated_optim_and_test_by_same_params = []

    # optim_result_0 = grid_optim_result[0]
    # test_result_0 = grid_optim_result_on_test[0]
    # print('optim_result_0')
    # print(optim_result_0)
    # print('test_result_0')
    # print(test_result_0)
    # optim_params_0 = optim_result_0[1:nb_of_params+1]
    # test_params_0 = test_result_0[1:nb_of_params+1]
    # print('optim_params_0')
    # print(optim_params_0)
    # print('test_params_0')
    # print(test_params_0)
    # test_result_without_params_0 = np.concatenate((test_result_0[0:1], test_result_0[nb_of_params+1:]))
    # print('test_result_without_params_0')
    # print(test_result_without_params_0)
    # concatenated_0 = np.concatenate((optim_result_0, test_result_without_params_0))
    # print('concatenated_0')
    # print(concatenated_0)
    # aggregated_optim_and_test_by_same_params.append(concatenated_0)

    for optim_result in grid_optim_result:
        optim_params = optim_result[1:nb_of_params+1]
        for test_result in grid_optim_result_on_test:
            test_params = test_result[1:nb_of_params+1]
            are_equal = np.array_equal(
                optim_params,
                test_params
            )
            if are_equal:
                test_result_without_params = np.concatenate((test_result[0:1], test_result[nb_of_params+1:]))
                concatenated = np.concatenate((optim_result, test_result_without_params))
                aggregated_optim_and_test_by_same_params.append(
                    concatenated
                )

    aggregated_optim_and_test_by_same_params_df = pd.DataFrame(aggregated_optim_and_test_by_same_params, columns=final_csv_column_names)

    return aggregated_optim_and_test_by_same_params_df