import numpy as np
from typing import Callable
from backtester.commons.ohlcv_type import TOhlcv
from backtester.strategy import backtest_strategy
from backtester.strategy.backtest_strategy import TBacktestResult
from backtester.strategy.optimize_strategy_grid import TGridOptimizationSetupTuple, grid_optimize
from backtester.strategy.strategy import Strategy, TBacktestSetup, TStrategyParams
from backtester.strategy.utils.optimize_and_test_loop.optimize_and_test_loop import optimize_and_test_loop

def grid_optimize_and_test_loop(
    grid_optimization_setup: TGridOptimizationSetupTuple,
    strategy: Strategy,
    data: TOhlcv,
    backtest_setup: TBacktestSetup,
    maximize_fn: Callable[[
        TBacktestResult,
        TStrategyParams,
    ], tuple[float, np.ndarray]],
    nb_of_candles_to_optimize_on: int,
    nb_of_candles_to_test_on: int,
    nb_of_candles_for_step: int,
    filter_possibility_fn: Callable[[
        TStrategyParams
    ], bool] | None = None,
    nb_of_processes: int = 1,
    parse_test_result_fn: Callable[[
        TBacktestResult,
    ], np.ndarray] | None = None,
):
    def optimize_fn(
        optimize_indices: np.ndarray,
    ):
        data_to_optimize_on = data[int(optimize_indices[0]):int(optimize_indices[1])]
        grid_optim_result = grid_optimize(
            grid_optimization_setup=grid_optimization_setup,
            strategy=strategy,
            data=data_to_optimize_on,
            backtest_setup=backtest_setup,
            maximize_fn=maximize_fn,
            filter_possibility_fn=filter_possibility_fn,
            nb_of_processes=nb_of_processes,
        )
        best_params = grid_optim_result[0]
        return best_params
    
    def test_fn(
        test_indices: np.ndarray,
        params: np.ndarray,
    ) -> np.ndarray:
        data_to_test_on = data[int(test_indices[0]):int(test_indices[1])]
        exact_params = params[1:len(grid_optimization_setup[0])+1]
        base_result = backtest_strategy(
            strategy=strategy,
            data=data_to_test_on,
            setup=backtest_setup,
            params=exact_params,
            state_shape=(0,)
        )
        if parse_test_result_fn is not None:
            return parse_test_result_fn(base_result)
        else:
            return base_result
    
    return optimize_and_test_loop(
        optimize_fn=optimize_fn,
        test_fn=test_fn,
        data_len=len(data),
        nb_of_items_to_optimize_on=nb_of_candles_to_optimize_on,
        nb_of_items_to_test_on=nb_of_candles_to_test_on,
        nb_of_items_for_step=nb_of_candles_for_step,
    )