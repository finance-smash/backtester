import numpy as np
import talib

# Import constants directly from the low-level module to avoid circular dependency
from backtester.commons.type_commons import BUY_SIGNAL, SELL_SIGNAL, NO_SIGNAL


def ema_cross_signal(close: np.ndarray,
                     short: int = 10,
                     long: int = 50) -> np.ndarray:
    """Compute BUY / SELL / NO_SIGNAL series based on EMA crossover/under.

    Parameters
    ----------
    close : np.ndarray
        1-D array of close prices.
    short : int, default 10
        Short moving-average length.
    long : int,  default 50
        Long moving-average length.

    Returns
    -------
    np.ndarray
        1-D integer array with BUY_SIGNAL, SELL_SIGNAL or NO_SIGNAL per bar.
    """
    short_ema = talib.SMA(close, timeperiod=short)
    long_ema = talib.SMA(close, timeperiod=long)

    crossover = (short_ema > long_ema) & (np.roll(short_ema, 1) <= np.roll(long_ema, 1))
    crossunder = (short_ema < long_ema) & (np.roll(short_ema, 1) >= np.roll(long_ema, 1))

    signal = np.where(crossover, BUY_SIGNAL, NO_SIGNAL) + \
             np.where(crossunder, SELL_SIGNAL, NO_SIGNAL)
    # first bar always no signal to avoid indexing issues
    if signal.size > 0:
        signal[0] = NO_SIGNAL

    return signal