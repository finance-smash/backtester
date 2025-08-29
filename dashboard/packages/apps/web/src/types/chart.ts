export interface ChartCandle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ParsedOrder {
  size: number;
  stop_loss: number;
  take_profit: number;
  price: number;
  order_type: number;
  side: number;
  offset: number;
  candle_index: number;
  user_id: number;
}

export interface OrderMarker {
  time: number;
  position: 'above' | 'below';
  color: string;
  shape: 'circle' | 'square' | 'arrow';
  text: string;
  size: 'tiny' | 'small' | 'normal' | 'large';
}

export interface ParsedIndicator {
  [indicatorName: string]: number | null; // null for 'nan' values
}

export interface IndicatorSeries {
  name: string;
  data: Array<{ time: number; value: number }>;
  color: string;
}

export interface ChartData {
  candles: ChartCandle[];
  orders: ParsedOrder[];
  indicators?: ParsedIndicator[];
}
