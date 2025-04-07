import numpy as np
from backtester.commons import TOhlcv


def generate_optimize_and_test_indices(
    data_len: int,
    nb_of_items_to_optimize_on: int = 100,
    nb_of_items_to_test_on: int = 100,
    nb_of_items_for_step: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate optimization and test indices for sliding window approach.
    
    Args:
        data: OHLCV data array
        nb_of_items_to_optimize_on: Number of items to use for optimization
        nb_of_items_to_test_on: Number of items to use for testing
        nb_of_items_for_step: Step size for sliding window
        
    Returns:
        Tuple of (optimize_indices, test_indices) arrays
    """
    all_optimize_indices = np.empty((0, 2))
    all_test_indices = np.empty((0, 2))

    i = 0

    while i < data_len - nb_of_items_to_optimize_on:
        begin_optimize_index = i
        end_optimize_index = begin_optimize_index + nb_of_items_to_optimize_on

        begin_test_index = end_optimize_index
        end_test_index = min(begin_test_index + nb_of_items_to_test_on, data_len)
        
        all_optimize_indices = np.concatenate((all_optimize_indices, np.array([[begin_optimize_index, end_optimize_index]])))
        all_test_indices = np.concatenate((all_test_indices, np.array([[begin_test_index, end_test_index]])))

        i += nb_of_items_for_step

    return all_optimize_indices, all_test_indices 