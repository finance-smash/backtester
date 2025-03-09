from typing import Annotated, Literal
import numpy.typing as npt
import numpy as np

TPositionKeys = {
    "size": 0,
    "avg_price": 1,
    "pl": 2
}

POSITION__SIZE = TPositionKeys['size']
POSITION__AVG_PRICE = TPositionKeys['avg_price']
POSITION__PL = TPositionKeys['pl']

TPositionTuple = tuple[
    float, # size (positive for long, negative for short)
    float, # avg_price (average price of the position)
    float, # pl (profit and loss)
]

TPosition = TPositionTuple

TPositionTriple = tuple[
    TPosition, # classic position
    TPosition, # hedging position long
    TPosition, # hedging position short
]

TPositionArray = Annotated[
    npt.NDArray[np.float64],
    TPosition,
]

TPositionTripleArray = Annotated[
    npt.NDArray[np.float64],
    TPositionTriple,
]