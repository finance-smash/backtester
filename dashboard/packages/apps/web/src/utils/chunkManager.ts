import Papa from 'papaparse';
import type { ChartCandle } from '../types/chart';
import { parseGMTTime } from './timeUtils';

export interface ChunkInfo {
  index: number;
  startRow: number;
  endRow: number;
  totalRows: number;
  candles: ChartCandle[];
}

export class ChunkManager {
  private static readonly DEFAULT_CHUNK_SIZE = 1000;
  private fileContent: string = '';
  private totalRows: number = 0;
  private chunkSize: number;
  private _headers: string[] = []; // Store headers for potential future use
  private currentChunk: ChunkInfo | null = null;

  constructor(chunkSize: number = ChunkManager.DEFAULT_CHUNK_SIZE) {
    this.chunkSize = chunkSize;
  }

  /**
   * Initialize the chunk manager with a CSV file
   */
  async initializeWithFile(file: File, chunkSize?: number): Promise<void> {
    if (chunkSize) {
      this.chunkSize = chunkSize;
    }

    // Read file content
    this.fileContent = await this.readFileAsText(file);
    
    // Parse just the first few lines to get headers and count total rows
    const lines = this.fileContent.split('\n');
    this.totalRows = lines.length - 1; // Subtract 1 for header row
    
    // Extract headers from first line
    if (lines.length > 0) {
      this._headers = this.parseCSVLine(lines[0]);
    }
    
    console.log(`ChunkManager initialized: ${this.totalRows} rows, chunk size: ${this.chunkSize}`);
  }

  /**
   * Get information about chunks without loading data
   */
  getChunkMetadata(): { totalChunks: number; chunkSize: number; totalRows: number } {
    const totalChunks = Math.ceil(this.totalRows / this.chunkSize);
    return {
      totalChunks,
      chunkSize: this.chunkSize,
      totalRows: this.totalRows
    };
  }

  /**
   * Get CSV headers
   */
  getHeaders(): string[] {
    return [...this._headers];
  }

  /**
   * Load a specific chunk of candles
   */
  async loadChunk(chunkIndex: number): Promise<ChunkInfo> {
    const totalChunks = Math.ceil(this.totalRows / this.chunkSize);
    
    if (chunkIndex < 0 || chunkIndex >= totalChunks) {
      throw new Error(`Invalid chunk index: ${chunkIndex}. Valid range: 0-${totalChunks - 1}`);
    }

    const startRow = chunkIndex * this.chunkSize;
    const endRow = Math.min(startRow + this.chunkSize, this.totalRows);

    console.log(`Loading chunk ${chunkIndex}: rows ${startRow}-${endRow}`);

    // Extract the relevant lines for this chunk
    const lines = this.fileContent.split('\n');
    const headerLine = lines[0];
    const chunkLines = lines.slice(startRow + 1, endRow + 1); // +1 because first line is header
    
    // Create CSV content for this chunk
    const chunkCSV = [headerLine, ...chunkLines].join('\n');

    // Parse the chunk
    const candles = await this.parseCandlesCSV(chunkCSV);

    // Clear previous chunk to free memory
    if (this.currentChunk) {
      this.currentChunk.candles = [];
    }

    // Create new chunk info
    this.currentChunk = {
      index: chunkIndex,
      startRow,
      endRow,
      totalRows: this.totalRows,
      candles
    };

    console.log(`Loaded ${candles.length} candles for chunk ${chunkIndex}`);
    return this.currentChunk;
  }

  /**
   * Get the currently loaded chunk
   */
  getCurrentChunk(): ChunkInfo | null {
    return this.currentChunk;
  }

  /**
   * Load the next chunk
   */
  async loadNextChunk(): Promise<ChunkInfo | null> {
    if (!this.currentChunk) {
      return await this.loadChunk(0);
    }

    const totalChunks = Math.ceil(this.totalRows / this.chunkSize);
    const nextIndex = this.currentChunk.index + 1;
    
    if (nextIndex >= totalChunks) {
      return null; // No more chunks
    }

    return await this.loadChunk(nextIndex);
  }

  /**
   * Load the previous chunk
   */
  async loadPreviousChunk(): Promise<ChunkInfo | null> {
    if (!this.currentChunk) {
      return await this.loadChunk(0);
    }

    const prevIndex = this.currentChunk.index - 1;
    
    if (prevIndex < 0) {
      return null; // No previous chunks
    }

    return await this.loadChunk(prevIndex);
  }

  /**
   * Clear all data to free memory
   */
  clear(): void {
    this.fileContent = '';
    this.totalRows = 0;
    this._headers = [];
    if (this.currentChunk) {
      this.currentChunk.candles = [];
      this.currentChunk = null;
    }
  }

  private async readFileAsText(file: File): Promise<string> {
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

  private parseCSVLine(line: string): string[] {
    // Simple CSV line parser - could be enhanced for complex cases
    return line.split(',').map(field => field.trim().replace(/^"|"$/g, ''));
  }

  private parseCandlesCSV(csvContent: string): Promise<ChartCandle[]> {
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
}
