export declare const orderTypes: Readonly<{
    MARKET: 1;
    LIMIT: 2;
    STOP: 3;
}>;
export type OrderTypeKey = keyof typeof orderTypes;
export type OrderType = (typeof orderTypes)[OrderTypeKey];
export declare const sides: Readonly<{
    BUY: 1;
    SELL: 2;
    NO_SIDE: 0;
}>;
export type SideKey = keyof typeof sides;
export type Side = (typeof sides)[SideKey];
export declare const offsets: Readonly<{
    OPEN: 1;
    CLOSE: 2;
    BOTH: 3;
}>;
export type OffsetKey = keyof typeof offsets;
export type Offset = (typeof offsets)[OffsetKey];
export type Order = [
    size: number,
    stop_loss: number,
    take_profit: number,
    price: number,
    order_type: OrderType,
    side: Side,
    offset: Offset,
    candle_index: number,
    user_id: number
];
