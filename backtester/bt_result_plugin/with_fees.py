import numpy as np

from backtester.strategy.backtest_strategy import TBacktestResult

from .bt_result_plugin import TBtResultPlugin

def with_fees(fee_rate: float) -> TBtResultPlugin:
    def plugin(bt_result: TBacktestResult) -> np.ndarray:
        all_pls = bt_result[3]

        all_pls_size = all_pls[:, 2]
        all_pls_close = all_pls[:, 3]
        all_pls_avg_price = all_pls[:, 4]
        
        all_pls_pl_recalculated_with_fees = np.zeros((len(all_pls_size), 2))

        for i in range(len(all_pls_size)):
            size = all_pls_size[i]
            close = all_pls_close[i]
            avg_price = all_pls_avg_price[i]

            close_with_fees = close * (1 + fee_rate * (
                -1 if (size > 0) else 1
            ))
            avg_price_with_fees = avg_price * (1 + fee_rate * (
                1 if (size > 0) else -1
            ))

            pl_perc_with_fees = ((close_with_fees - avg_price_with_fees) / avg_price_with_fees) * np.sign(size)

            all_pls_pl_recalculated_with_fees[i, 0] = size * (close_with_fees - avg_price_with_fees)
            all_pls_pl_recalculated_with_fees[i, 1] = pl_perc_with_fees

        return all_pls_pl_recalculated_with_fees
    
    return plugin
