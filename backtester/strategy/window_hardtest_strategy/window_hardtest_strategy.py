from typing import Callable, Optional, Union
import os
from backtester.commons.ohlcv_type import TOhlcv
from backtester.strategy.optimize_strategy_grid import TFilterPossibilityFn, TGridOptimizationSetupTuple, TMaximizeFn,\
    grid_optimize
from backtester.strategy.strategy import Strategy, TBacktestSetup
from backtester.commons.helpers import get_ohlcv_data
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

    print('optimization_ohlcvs')
    print(optimization_ohlcvs[0][0], optimization_ohlcvs[0][-1])

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


def window_hardtest_strategy(
    strategy: Strategy,
    timeranges: tuple[str, ...],
    optimization_window_range: Union[range, list, np.ndarray],
    maximize_fn: TMaximizeFn,
    backtest_setup: TBacktestSetup,
    grid_optimization_setup: TGridOptimizationSetupTuple,
    filter_possibility_fn: Optional[TFilterPossibilityFn] = None,
    crypto_pairs: Optional[list[str]] = None,
    nb_of_processes: int = 1,
    begin_at_index: int = 0,
    data_dir: str = "/Users/dyodio/Documents/Projects/Finance-Smash/data",
    output_dir: str = "csvResults"
) -> list[str]:
    """
    Perform comprehensive window hardtest strategy across multiple timeframes and crypto pairs.
    
    Args:
        strategy: The trading strategy to test
        timeranges: Tuple of timeframes to test on ('1d', '1h', '1w', '4h', '5min', '15min')
        optimization_window_range: Range of optimization window sizes to test
        maximize_fn: Function to maximize during optimization
        backtest_setup: Backtest configuration
        grid_optimization_setup: Grid optimization parameters
        filter_possibility_fn: Optional function to filter parameter combinations
        crypto_pairs: Optional list of crypto pairs to test (if None, uses default list)
        nb_of_processes: Number of processes for parallel execution
        begin_at_index: Starting index for data processing
        data_dir: Directory containing the data files
        output_dir: Directory to save output CSV files
        
    Returns:
        List of file paths for created CSV files
    """
    
    # Default crypto pairs if none provided
    if crypto_pairs is None:
        crypto_pairs = [
            'ADA-USDT', 'AGIX-USDT', 'APT-USDT', 'ARB-USDT', 'ATOM-USDT',
            'AVAX-USDT', 'AXS-USDT', 'BCH-USDT', 'BEAM-USDT', 'BNB-USDT',
            'BTC-USDT', 'BTT-USDT', 'CFX-USDT', 'CHZ-USDT', 'DAI-USDT',
            'DOGE-USDT', 'DOT-USDT', 'DYDX-USDT', 'EGLD-USDT', 'ENA-USDT',
            'ENS-USDT', 'EOS-USDT', 'ETC-USDT', 'ETH-USDT', 'GALA-USDT',
            'GNO-USDT', 'HBAR-USDT', 'ICP-USDT', 'LINK-USDT', 'LTC-USDT',
            'MATIC-USDT', 'NEAR-USDT', 'NEO-USDT', 'NEXO-USDT', 'ORDI-USDT',
            'PENDLE-USDT', 'PEPE-USDT', 'QNT-USDT', 'RNDR-USDT', 'SAND-USDT',
            'SHIB-USDT', 'SNX-USDT', 'SOL-USDT', 'TON-USDT', 'TRX-USDT',
            'UNI-USDT', 'WLD-USDT', 'XLM-USDT', 'XMR-USDT', 'XRP-USDT',
            'XTZ-USDT', 'ZRO-USDT'
        ]
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    created_files = []
    
    # Convert ranges to lists if needed
    if isinstance(optimization_window_range, range):
        optimization_window_range = list(optimization_window_range)
    elif isinstance(optimization_window_range, np.ndarray):
        optimization_window_range = optimization_window_range.tolist()
    
    print(f"Starting window hardtest for {len(timeranges)} timeranges, {len(crypto_pairs)} cryptos, {len(optimization_window_range)} window sizes...")
    
    combination_count = 0
    
    for timerange in timeranges:
        print(f"Processing timerange: {timerange}")
        
        for crypto in crypto_pairs:
            print(f"  Processing crypto: {crypto}")
            
            # Load OHLCV data for this crypto and timerange
            try:
                ohlcv_data, _ = get_ohlcv_data('crypto', crypto, timerange, data_dir)
            except Exception as e:
                print(f"    Error loading data for {crypto} {timerange}: {e}")
                continue
            
            for optimization_window in optimization_window_range:
                # Calculate maximum number of optimization windows based on data length
                # Following the pattern: (len(ohlcv_data) - begin_at_index) // optimization_window
                nb_of_optimization_windows = (len(ohlcv_data) - begin_at_index) // optimization_window
                
                # Need at least 2 windows (1 for optimization, 1 for testing)
                if nb_of_optimization_windows < 2:
                    print(f"    Skipping {crypto} {timerange} window={optimization_window}: "
                          f"insufficient data for at least 2 windows (calculated {nb_of_optimization_windows})")
                    continue
                
                
                combination_count += 1
                print(f"    Processing combination {combination_count}: "
                      f"window={optimization_window}, nb_windows={nb_of_optimization_windows} "
                      f"(data_length={len(ohlcv_data)})")
                
                # Generate filename with all parameters
                file_name = f'window_hardtest_{crypto}_{timerange}_optwin{optimization_window}_nbwin{nb_of_optimization_windows}_beginat{begin_at_index}.csv'
                file_path = os.path.join(output_dir, file_name)
                
                # Skip if file already exists
                if os.path.exists(file_path):
                    print(f"      File already exists: {file_name}")
                    created_files.append(file_path)
                    continue
                
                # Generate column names based on the number of optimization windows
                pl_len_cols = [f'pl_len_{i}' for i in range(nb_of_optimization_windows)]
                pl_perc_cols = [f'pl_perc_{i}' for i in range(nb_of_optimization_windows)]
                base_columns = ['maximize_value', 'long_ma_len', 'short_ma_len', 'std_dev_mult']
                columns = base_columns + pl_len_cols + pl_perc_cols
                new_columns = columns + ['pl_test_min', 'pl_test_len', 'pl_test_mean_perc']
                
                try:
                    # Run the window hardtest
                    df = window_hardtest_strategy_inner(
                        ohlcv=ohlcv_data,
                        optimization_window=optimization_window,
                        nb_of_optimization_windows=nb_of_optimization_windows,
                        test_window=optimization_window,
                        maximize_fn=maximize_fn,
                        strategy=strategy,
                        backtest_setup=backtest_setup,
                        grid_optimization_setup=grid_optimization_setup,
                        final_csv_column_names=new_columns,
                        filter_possibility_fn=filter_possibility_fn,
                        nb_of_test_windows=1,
                        first_optimization_window_index=0,
                        nb_of_processes=nb_of_processes,
                        begin_at_index=begin_at_index,
                    )
                    
                    # Save to CSV
                    df.to_csv(file_path, index=False)
                    created_files.append(file_path)
                    print(f"      Created: {file_name}")
                    
                except Exception as e:
                    print(f"      Error processing combination: {e}")
                    continue
    
    print(f"Window hardtest completed. Created {len(created_files)} files.")
    return created_files