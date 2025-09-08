"""
Example usage of the abstracted window_hardtest_strategy function.

This demonstrates how to use the new clean API to run comprehensive 
window hardtests across multiple timeframes and crypto pairs.
"""

import numpy as np
from backtester.examples.limit_mean_rev.strategy import LimitMeanRevStrategy, maximize_fn2, PARAMS__LONG_MA_LEN, PARAMS__SHORT_MA_LEN
from backtester.strategy.backtest_strategy import make_backtest_setup_tuple
from backtester.strategy.window_hardtest_strategy.window_hardtest_strategy import window_hardtest_strategy


def run_example_window_hardtest():
    """Example demonstrating the abstracted window hardtest function."""
    
    # Define strategy parameters to optimize over
    all_params = [
        np.arange(5000, 10000, 1000),
        np.arange(20, 100, 5),
        np.arange(2, 3, 0.25),
    ]
    
    # Create backtest setup
    backtest_setup = make_backtest_setup_tuple(
        begin_equity=100_000_000_00,
        is_hedged=1,
        auto_trigger_tp_sl=True,
        return_order_history=False
    )
    
    # Define test parameters
    timeranges_to_test = ('15min',)  # Test on 5min and 15min timeframes
    optimization_window_range = [10000]  # Test window sizes of 20k and 30k
    # Note: nb_of_optimization_windows is now calculated automatically based on data length
    
    # Select a few cryptos for demonstration (faster execution)
    # test_cryptos = ['BTC-USDT']
    test_cryptos = None
    
    print("Starting abstracted window hardtest example...")
    print(f"Testing on timeranges: {timeranges_to_test}")
    print(f"Testing on cryptos: {test_cryptos}")
    print(f"Optimization windows: {optimization_window_range}")
    print("Number of optimization windows: calculated automatically based on data length")
    
    # Run the abstracted window hardtest
    created_files = window_hardtest_strategy(
        strategy=LimitMeanRevStrategy,
        timeranges=timeranges_to_test,
        optimization_window_range=optimization_window_range,
        maximize_fn=maximize_fn2,
        backtest_setup=backtest_setup,
        grid_optimization_setup=(all_params, 0),
        filter_possibility_fn=lambda params: params[PARAMS__LONG_MA_LEN] > params[PARAMS__SHORT_MA_LEN],
        crypto_pairs=test_cryptos,
        nb_of_processes=8,
        begin_at_index=10000,
        data_dir="/Users/dyodio/Documents/Projects/Finance-Smash/data",
        output_dir="csvResultsWithFees15mn"
    )
    
    print(f"\nCompleted! Created {len(created_files)} files:")
    for file_path in created_files:
        print(f"  {file_path}")
    
    return created_files


if __name__ == '__main__':
    # Uncomment the line below to run the example
    run_example_window_hardtest()
