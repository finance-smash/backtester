import numpy as np
from typing import Callable

from backtester.strategy.utils.generate_optimize_and_test_indices import generate_optimize_and_test_indices

def optimize_and_test_loop(
    optimize_fn: Callable[[np.ndarray], np.ndarray],
    test_fn: Callable[[np.ndarray], np.ndarray],
    data_len: int,
    nb_of_items_to_optimize_on: int = 100000,
    nb_of_items_to_test_on: int = 100000,
    nb_of_items_for_step: int = 100000,
):
    all_optimize_indices, all_test_indices = generate_optimize_and_test_indices(
        data_len=data_len,
        nb_of_items_to_optimize_on=nb_of_items_to_optimize_on,
        nb_of_items_to_test_on=nb_of_items_to_test_on,
        nb_of_items_for_step=nb_of_items_for_step,
    )

    nb_of_runs = len(all_optimize_indices)

    all_results = {}

    for run_index in range(nb_of_runs):
        optimize_indices = all_optimize_indices[run_index]
        test_indices = all_test_indices[run_index]

        optimized_params: np.ndarray = optimize_fn(
            optimize_indices=optimize_indices,
        )

        test_result: np.ndarray = test_fn(
            test_indices=test_indices,
            params=optimized_params,
        )

        all_results[run_index] = {
            'optimize_indices': optimize_indices,
            'test_indices': test_indices,
            'optimized_params': optimized_params,
            'test_result': test_result,
        }

    return all_results