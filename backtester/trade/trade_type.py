import numpy.typing as npt
import numpy as np

from typing_extensions import Annotated, Literal
from commons.type_commons import TBuy, TSell



TTradeKeys = {
    "entry_price": 0,
    "size": 1,
    "side": 2,
    "pl": 3,
    "pl_percentage": 4
}

TRADE__ENTRY_PRICE = TTradeKeys['entry_price']
TRADE__SIZE = TTradeKeys['size']
TRADE__SIDE = TTradeKeys['side']
TRADE__PL = TTradeKeys['pl']
TRADE__PL_PERCENTAGE = TTradeKeys['pl_percentage']

TTradeTuple = tuple[
    float, # entry_price
    float, # size
    TBuy | TSell, # side
    float, # pl
    float, # pl_percentage
]

TTrade = Annotated[npt.NDArray[np.float64], TTradeTuple]

TTrades = Annotated[
    npt.NDArray[np.float64],
    TTradeTuple,
    Literal["N"]
]