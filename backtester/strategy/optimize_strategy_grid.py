import numpy as np
import numpy.typing as npt
from typing import Callable
from itertools import product
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
from functools import partial

from numba import njit # type: ignore

from backtester.strategy.strategy import Strategy, TStrategyParams
from backtester.strategy.backtest_strategy import TBacktestSetup, TBacktestResult, backtest_strategy
from backtester.commons import TOhlcv

TGridOptimizationSetupTuple = tuple[
    list[np.float64], #all arrays of parameters in order
    int, #max number of tries, if 0 all tries are done
]

TFilterPossibilityFn = Callable[[
    TStrategyParams
], bool] | None

TMaximizeFn = Callable[[
    list[tuple[TBacktestResult, TStrategyParams]],
], tuple[float, np.ndarray]]



def process_batch(batch_data, strategy, data, backtest_setup, maximize_fn, begin_at_index):
    """Process a single batch of possibilities"""
    batch_results = []
    for params in batch_data:
        maximize_fn_input = []
        for data_item in data:
            bt_result = backtest_strategy(
                strategy=strategy,
                data=data_item,
                setup=backtest_setup,
                params=params,
                begin_at_index=begin_at_index,
            )
            maximize_fn_input.append((bt_result, params))
        [to_maximize_value, maximize_fn_infos] = maximize_fn(maximize_fn_input)
        to_append = np.concatenate(([
            [to_maximize_value],
            params,
            maximize_fn_infos,
        ]))
        batch_results.append(to_append)
    return batch_results



def task_wrapper(args):
    return process_batch(*args)



def grid_optimize_inner(
    strategy: Strategy,
    all_possibilities: npt.NDArray[np.float64],
    data: list[TOhlcv],
    backtest_setup: TBacktestSetup,
    maximize_fn: Callable[[
        list[tuple[TBacktestResult, TStrategyParams]],
    ], tuple[float, np.ndarray]],
    nb_of_processes: int = 1,
    begin_at_index: int = 0,
):
    nb_of_possibilities = len(all_possibilities)
    if nb_of_processes <= 1:
        opti_result = []
        # data_as_list = data if isinstance(data, list) else [data]
        for i in tqdm(range(0, nb_of_possibilities), desc="Optimizing strategy"):
            params = all_possibilities[i]
            maximize_fn_input = []
            data_item = data[0]
            for data_item in data:
                bt_result = backtest_strategy(
                    strategy=strategy,
                    data=data_item,
                    setup=backtest_setup,
                    params=params,
                    begin_at_index=begin_at_index,
                )
                maximize_fn_input.append((bt_result, params))
            [to_maximize_value, maximize_fn_infos] = maximize_fn(maximize_fn_input)
            to_append = np.concatenate(([
                [to_maximize_value],
                params,
                maximize_fn_infos,
            ]))
            opti_result.append(to_append)
    else:
        nb_of_processes = min(nb_of_processes, cpu_count())
        print(f"nb_of_processes: {nb_of_processes}")
        batch_size = nb_of_possibilities // nb_of_processes
        remaining_batch_size = nb_of_possibilities % nb_of_processes
        print(f"batch_size: {batch_size}")
        print(f"remaining_batch_size: {remaining_batch_size}")
        batches = [all_possibilities[i:i + batch_size] for i in range(0, nb_of_possibilities, batch_size)]
        if remaining_batch_size > 0:
            batches.append(all_possibilities[-remaining_batch_size:])

        batches_arg_list = list(map(lambda x: (x, strategy, data, backtest_setup, maximize_fn, begin_at_index), batches))
        print("batches_arg_list len")
        print(len(batches_arg_list))
        with Pool(nb_of_processes) as pool:
            results = list(tqdm(
                pool.imap(task_wrapper, batches_arg_list),
                total=len(batches_arg_list),
                desc="Optimizing strategy"
            ))
        
        opti_result = [item for batch in results for item in batch]
    opti_result = np.array(opti_result)

    sorted_indices = np.argsort(opti_result[:, 0])[::-1]
    sorted_opti_result = opti_result[sorted_indices]

    return sorted_opti_result



def grid_optimize(
    grid_optimization_setup: TGridOptimizationSetupTuple,
    strategy: Strategy,
    data: list[TOhlcv],
    backtest_setup: TBacktestSetup,
    maximize_fn: TMaximizeFn,
    filter_possibility_fn: TFilterPossibilityFn = None,
    nb_of_processes: int = 1,
    begin_at_index: int = 0
):
    [all_params_possibilities, max_tries] = grid_optimization_setup
    all_possibilities = get_cartesian_product(all_params_possibilities)
    if filter_possibility_fn is not None or max_tries > 0:
        final_possibilities = []
        i = 0
        for possibility in all_possibilities:
            if max_tries > 0 and i >= max_tries:
                break
            if filter_possibility_fn is None or filter_possibility_fn(possibility):
                final_possibilities.append(possibility)
                i += 1
    else:
        final_possibilities = all_possibilities
    all_possibilities = np.array(final_possibilities)
    return grid_optimize_inner(
        strategy=strategy,
        all_possibilities=all_possibilities,
        data=data,
        backtest_setup=backtest_setup,
        maximize_fn=maximize_fn,
        nb_of_processes=nb_of_processes,
        begin_at_index=begin_at_index,
    )

        

def get_cartesian_product(all_params_possibilities):
    """
    Compute the cartesian product of arrays.
    
    Args:
        all_params_possibilities: List of lists containing all possible values for each parameter
        
    Returns:
        List of lists containing all possible combinations
    """
    return list(product(*all_params_possibilities))