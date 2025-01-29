from typing import Literal


TBUY = Literal[1]
TSell = Literal[2]
TSide = Literal[TBUY, TSell]

BUY: TBUY = 1
SELL: TSell = 2

BUY_SIGNAL = BUY
SELL_SIGNAL = SELL
NO_SIGNAL = 0