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