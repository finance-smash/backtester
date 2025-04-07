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



def process_batch(batch_data, strategy, data, backtest_setup, maximize_fn):
    """Process a single batch of possibilities"""
    batch_results = []
    for params in batch_data:
        bt_result = backtest_strategy(
            strategy=strategy,
            data=data,
            setup=backtest_setup,
            params=params,
        )
        [to_maximize_value, maximize_fn_infos] = maximize_fn(bt_result, params)
        to_append = np.concatenate(([
            [to_maximize_value],
            params,
            maximize_fn_infos,
        ]))
        batch_results.append(to_append)
    return batch_results

def task_wrapper(args):
    return process_batch(*args)


def test_fn(x: int):
    return x*2

test_batch = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

def _run_parallel_optimization(batches, process_batch_partial, nb_of_processes):
    """Helper function to run parallel optimization"""
    with Pool(nb_of_processes) as pool:
        print("pool")
        print(pool)
        results = pool.map(process_batch_partial, batches)
        results_test = pool.map(test_fn, test_batch)
        print("results_test")
        print(results_test)
        print("results")
        print(results)
    return results



def grid_optimize_inner(
    strategy: Strategy,
    all_possibilities: npt.NDArray[np.float64],
    data: TOhlcv,
    backtest_setup: TBacktestSetup,
    maximize_fn: Callable[[
        TBacktestResult,
        TStrategyParams,
    ], tuple[
        float, # to maximize value
        np.ndarray # maximize infos
    ]],
    nb_of_processes: int = 1
):
    nb_of_possibilities = len(all_possibilities)
    if nb_of_processes <= 1:
        opti_result = []
        for i in tqdm(range(0, nb_of_possibilities), desc="Optimizing strategy"):
            params = all_possibilities[i]
            bt_result = backtest_strategy(
                strategy=strategy,
                data=data,
                setup=backtest_setup,
                params=params,
            )
            [to_maximize_value, maximize_fn_infos] = maximize_fn(bt_result, params)
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
        batches = [all_possibilities[i:i + batch_size] for i in range(0, nb_of_possibilities, batch_size)]
        
        # Create a partial function with the fixed arguments
        # def process_batch_partial(batch_data):
        #     return process_batch(
        #         batch_data=batch_data,
        #         strategy=strategy,
        #         data=data,
        #         backtest_setup=backtest_setup,
        #         maximize_fn=maximize_fn
        #     )
        
        # Process batches in parallel
        # Process batches in parallel
        # results = _run_parallel_optimization(batches, process_batch_partial, nb_of_processes)
        batches_arg_list = list(map(lambda x: (x, strategy, data, backtest_setup, maximize_fn), batches))
        print("batches_arg_list")
        print(batches_arg_list)
        with Pool(nb_of_processes) as pool:
            # print("pool")
            # print(pool)
            # results = pool.map(task_wrapper, batches_arg_list)
            results = list(tqdm(
                pool.imap(task_wrapper, batches_arg_list),
                total=len(batches_arg_list),
                desc="Optimizing strategy"
            ))
            results_test = pool.map(test_fn, test_batch)
            print("results_test")
            print(results_test)
            # print("results")
            # print(results)
        
        # Flatten results from all batches
        opti_result = [item for batch in results for item in batch]
    opti_result = np.array(opti_result)

    sorted_indices = np.argsort(opti_result[:, 0])[::-1]
    sorted_opti_result = opti_result[sorted_indices]

    return sorted_opti_result



def grid_optimize(
    grid_optimization_setup: TGridOptimizationSetupTuple,
    strategy: Strategy,
    data: TOhlcv,
    backtest_setup: TBacktestSetup,
    maximize_fn: Callable[[
        TBacktestResult,
        TStrategyParams,
    ], tuple[float, np.ndarray]],
    filter_possibility_fn: Callable[[
        TStrategyParams
    ], bool] | None = None,
    nb_of_processes: int = 1
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
        nb_of_processes=nb_of_processes
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


# if __name__ == '__main__':
    # with Pool(4) as pool:
    #     # results = pool.map(process_batch_partial, batches)
    #     results = pool.map(test_fn, test_batch)
    #     print("results")
    #     print(results)
    #     # results = list(tqdm(
    #     #     pool.map(process_batch_partial, batches),
    #     #     total=len(batches),
    #     #     desc="Optimizing strategy"
    #     # ))

    # _run_parallel_optimization(
    #     batches=None,
    #     process_batch_partial=None,
    #     nb_of_processes=4
    # )