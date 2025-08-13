import Papa from 'papaparse';
import type { ChartCandle, ParsedOrder } from '../types/chart';
import { ChunkManager } from './chunkManager';
import { parseGMTTime } from './timeUtils';

export class CSVParser {
  /**
   * Create a chunk manager for large candle files
   */
  static async createChunkManager(file: File, chunkSize?: number): Promise<ChunkManager> {
    const chunkManager = new ChunkManager(chunkSize);
    await chunkManager.initializeWithFile(file, chunkSize);
    return chunkManager;
  }

  static parseCandlesCSV(csvContent: string): Promise<ChartCandle[]> {
    return new Promise((resolve, reject) => {
      Papa.parse(csvContent, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          try {
            const candles: ChartCandle[] = results.data.map((row: any) => {
              const gmtTime = parseGMTTime(row['Gmt time']);
              
              return {
                time: gmtTime,
                open: parseFloat(row['Open']),
                high: parseFloat(row['High']),
                low: parseFloat(row['Low']),
                close: parseFloat(row['Close']),
                volume: parseFloat(row['Volume'])
              };
            }).filter(candle => !isNaN(candle.time));
            
            resolve(candles);
          } catch (error) {
            reject(new Error(`Failed to parse candles CSV: ${error}`));
          }
        },
        error: (error: any) => {
          reject(new Error(`CSV parsing error: ${error}`));
        }
      });
    });
  }

  static parseOrdersCSV(csvContent: string): Promise<ParsedOrder[]> {
    return new Promise((resolve, reject) => {
      Papa.parse(csvContent, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          try {
            const orders: ParsedOrder[] = results.data.map((row: any) => ({
              size: parseFloat(row['size']),
              stop_loss: parseFloat(row['stop_loss']),
              take_profit: parseFloat(row['take_profit']),
              price: parseFloat(row['price']),
              order_type: parseFloat(row['order_type']),
              side: parseFloat(row['side']),
              offset: parseFloat(row['offset']),
              candle_index: parseFloat(row['candle_index']),
              user_id: parseFloat(row['user_id'])
            })).filter(order => !isNaN(order.price));
            
            resolve(orders);
          } catch (error) {
            reject(new Error(`Failed to parse orders CSV: ${error}`));
          }
        },
        error: (error: any) => {
          reject(new Error(`CSV parsing error: ${error}`));
        }
      });
    });
  }

  static async parseFile(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result;
        if (typeof result === 'string') {
          resolve(result);
        } else {
          reject(new Error('Failed to read file as text'));
        }
      };
      reader.onerror = () => reject(new Error('Error reading file'));
      reader.readAsText(file);
    });
  }
}
