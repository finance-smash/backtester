from typing import Literal


TBUY = Literal[1]
TSell = Literal[2]
TNoSide = Literal[0]
TSide = Literal[TBUY, TSell, TNoSide]

BUY: TBUY = 1
SELL: TSell = 2
NO_SIDE: TNoSide = 0

BUY_SIGNAL = BUY
SELL_SIGNAL = SELL
NO_SIGNAL = NO_SIDE