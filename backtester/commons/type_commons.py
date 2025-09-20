from typing import Literal



TBuy = Literal[1]
TSell = Literal[2]
TNoSide = Literal[0]
TSide = Literal[TBuy, TSell, TNoSide]

BUY: TBuy = 1
SELL: TSell = 2
NO_SIDE: TNoSide = 0

BUY_SIGNAL = BUY
SELL_SIGNAL = SELL
NO_SIGNAL = NO_SIDE

TOrderTypeMarket = Literal[1]
TOrderTypeLimit = Literal[2]
TOrderTypeStop = Literal[3]

ORDER_TYPE__MARKET: TOrderTypeMarket = 1
ORDER_TYPE__LIMIT: TOrderTypeLimit = 2
ORDER_TYPE__STOP: TOrderTypeStop = 3

TOrderType = Literal[
    TOrderTypeMarket,
    TOrderTypeLimit,
    TOrderTypeStop,
]

TBoolInt = Literal[0, 1]

TOffsetOpen = Literal[1]
TOffsetClose = Literal[2]
TOffsetBoth = Literal[3]

OFFSET__OPEN: TOffsetOpen = 1
OFFSET__CLOSE: TOffsetClose = 2
OFFSET__BOTH: TOffsetBoth = 3

TOffset = Literal[
    TOffsetOpen,
    TOffsetClose,
    TOffsetBoth,
]

TOhlcvDataDomain = Literal['crypto', 'forex']
TOhlcvDataSymbol = str
TOhlcvDataTimeframe = Literal['1d', '1h', '1w', '4h', '5min', '15min']
TOhlcvDataPathTuple = tuple[TOhlcvDataDomain, TOhlcvDataSymbol, TOhlcvDataTimeframe]