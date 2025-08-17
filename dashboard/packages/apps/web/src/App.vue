<script setup lang="ts">
import { ref, computed } from 'vue';
import { TradingChart, FileUpload, ChunkControls } from './components';
import { CSVParser } from './utils/csvParser';
import type { ChartCandle, ParsedOrder } from './types/chart';
import type { ChunkManager, ChunkInfo } from './utils/chunkManager';

const candles = ref<ChartCandle[]>([]);
const orders = ref<ParsedOrder[]>([]);
const candlesLoading = ref(false);
const ordersLoading = ref(false);
const error = ref<string>('');

// Chunk-related state
const chunkManager = ref<ChunkManager | null>(null);
const currentChunkInfo = ref<ChunkInfo | null>(null);
const chunkMetadata = ref<{ totalChunks: number; chunkSize: number; totalRows: number } | null>(null);

// Computed property to get the number of orders in the current chunk
const ordersInCurrentChunk = computed(() => {
  if (!currentChunkInfo.value || orders.value.length === 0) return 0;
  
  const startRow = currentChunkInfo.value.startRow;
  const endRow = currentChunkInfo.value.endRow;
  
  return orders.value.filter(order => {
    const globalIndex = Math.floor(order.candle_index);
    return globalIndex >= startRow && globalIndex < endRow;
  }).length;
});

const handleCandlesFile = async (file: File) => {
  candlesLoading.value = true;
  error.value = '';
  
  try {
    // Check file size to determine if we should use chunking
    const fileSizeInMB = file.size / (1024 * 1024);
    const shouldUseChunking = fileSizeInMB > 10; // Use chunking for files larger than 10MB
    
    if (shouldUseChunking) {
      // Use chunk loading for large files
      const manager = await CSVParser.createChunkManager(file, 1000);
      chunkManager.value = manager;
      chunkMetadata.value = manager.getChunkMetadata();
      
      // Load the first chunk
      const chunkInfo = await manager.loadChunk(0);
      currentChunkInfo.value = chunkInfo;
      candles.value = chunkInfo.candles;
      
      console.log(`Large file detected (${fileSizeInMB.toFixed(1)}MB). Using chunk loading with ${chunkMetadata.value.totalChunks} chunks.`);
    } else {
      // Use traditional loading for smaller files
      const csvContent = await CSVParser.parseFile(file);
      const parsedCandles = await CSVParser.parseCandlesCSV(csvContent);
      candles.value = parsedCandles;
      
      // Clear chunk-related state
      chunkManager.value = null;
      chunkMetadata.value = null;
      currentChunkInfo.value = null;
      
      console.log(`Small file (${fileSizeInMB.toFixed(1)}MB). Using traditional loading.`);
    }
  } catch (err) {
    error.value = `Error loading candles: ${err instanceof Error ? err.message : 'Unknown error'}`;
  } finally {
    candlesLoading.value = false;
  }
};

const handleOrdersFile = async (file: File) => {
  ordersLoading.value = true;
  error.value = '';
  
  try {
    const csvContent = await CSVParser.parseFile(file);
    const parsedOrders = await CSVParser.parseOrdersCSV(csvContent);
    orders.value = parsedOrders;
  } catch (err) {
    error.value = `Error loading orders: ${err instanceof Error ? err.message : 'Unknown error'}`;
  } finally {
    ordersLoading.value = false;
  }
};

// Chunk navigation handlers
const goToFirstChunk = async () => {
  if (!chunkManager.value) return;
  await loadChunk(0);
};

const goToPreviousChunk = async () => {
  if (!chunkManager.value || !currentChunkInfo.value) return;
  const prevIndex = currentChunkInfo.value.index - 1;
  if (prevIndex >= 0) {
    await loadChunk(prevIndex);
  }
};

const goToNextChunk = async () => {
  if (!chunkManager.value || !currentChunkInfo.value || !chunkMetadata.value) return;
  const nextIndex = currentChunkInfo.value.index + 1;
  if (nextIndex < chunkMetadata.value.totalChunks) {
    await loadChunk(nextIndex);
  }
};

const goToLastChunk = async () => {
  if (!chunkManager.value || !chunkMetadata.value) return;
  await loadChunk(chunkMetadata.value.totalChunks - 1);
};

const goToChunk = async (chunkIndex: number) => {
  await loadChunk(chunkIndex);
};

const changeChunkSize = async (_newSize: number) => {
  if (!chunkManager.value) return;
  
  // Clear current data
  chunkManager.value.clear();
  candles.value = [];
  currentChunkInfo.value = null;
  chunkMetadata.value = null;
  
  // Note: We can't easily change chunk size without re-reading the file
  // For now, we'll just show an error message suggesting to reload the file
  error.value = 'To change chunk size, please reload the candles file.';
};

const loadChunk = async (chunkIndex: number) => {
  if (!chunkManager.value) return;
  
  candlesLoading.value = true;
  error.value = '';
  
  try {
    const chunkInfo = await chunkManager.value.loadChunk(chunkIndex);
    currentChunkInfo.value = chunkInfo;
    candles.value = chunkInfo.candles;
  } catch (err) {
    error.value = `Error loading chunk: ${err instanceof Error ? err.message : 'Unknown error'}`;
  } finally {
    candlesLoading.value = false;
  }
};

const clearCandles = () => {
  candles.value = [];
  error.value = '';
  
  // Clear chunk-related state
  if (chunkManager.value) {
    chunkManager.value.clear();
  }
  chunkManager.value = null;
  chunkMetadata.value = null;
  currentChunkInfo.value = null;
};

const clearOrders = () => {
  orders.value = [];
  error.value = '';
};
</script>

<template>
  <div class="app">
    <header class="app-header">
      <h1>💰 Finance Smash Analysis Dashboard</h1>
      <p>Load candle data and visualize trading orders on interactive charts</p>
    </header>

    <main class="app-main">
      <div class="controls-section">
        <div class="upload-grid">
          <FileUpload
            title="Load Candles Data"
            description="CSV format: Gmt time, Open, High, Low, Close, Volume (Times displayed as GMT)"
            :loading="candlesLoading"
            @file-selected="handleCandlesFile"
            @file-cleared="clearCandles"
          />
          
          <FileUpload
            title="Load Orders Data"
            description="CSV format: size, stop_loss, take_profit, price, order_type, side, offset, candle_index, user_id"
            :loading="ordersLoading"
            @file-selected="handleOrdersFile"
            @file-cleared="clearOrders"
          />
        </div>

        <div v-if="error" class="error-banner">
          {{ error }}
        </div>

        <div class="data-status">
          <div class="status-item" :class="{ active: candles.length > 0 }">
            📊 Candles: {{ candles.length }} loaded
            <span v-if="chunkMetadata" class="chunk-info-mini">
              (Chunk {{ (currentChunkInfo?.index ?? 0) + 1 }}/{{ chunkMetadata.totalChunks }})
            </span>
          </div>
          <div class="status-item" :class="{ active: orders.length > 0 }">
            📈 Orders: {{ orders.length }} loaded
          </div>
        </div>

        <!-- Chunk Controls (only shown when using chunked loading) -->
        <ChunkControls
          v-if="chunkMetadata"
          :chunk-metadata="chunkMetadata"
          :current-chunk="currentChunkInfo?.index ?? 0"
          :loading="candlesLoading"
          :orders-in-chunk="ordersInCurrentChunk"
          @go-to-first-chunk="goToFirstChunk"
          @go-to-previous-chunk="goToPreviousChunk"
          @go-to-next-chunk="goToNextChunk"
          @go-to-last-chunk="goToLastChunk"
          @go-to-chunk="goToChunk"
          @change-chunk-size="changeChunkSize"
        />
      </div>

      <div class="chart-section">
        <div v-if="candles.length === 0" class="chart-placeholder">
          <div class="placeholder-content">
            <div class="placeholder-icon">📈</div>
            <h3>No Data Loaded</h3>
            <p>Please upload a candles CSV file to start visualizing your trading data</p>
          </div>
        </div>
        
        <TradingChart
          v-else
          :candles="candles"
          :orders="orders"
          :chunk-start-index="currentChunkInfo?.startRow"
          :chunk-end-index="currentChunkInfo?.endRow"
          style="flex: 1; display: flex; flex-direction: column;"
        />
      </div>
    </main>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  width: 100vw;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 0.75rem;
  box-sizing: border-box;
  overflow-y: auto;
  overflow-x: hidden;
}

.app-header {
  text-align: center;
  color: white;
  margin-bottom: 1.5rem;
}

.app-header h1 {
  font-size: 2rem;
  margin: 0 0 0.25rem 0;
  font-weight: 700;
}

.app-header p {
  font-size: 1rem;
  margin: 0;
  opacity: 0.9;
}

.app-main {
  max-width: none;
  width: 100%;
  min-height: calc(100vh - 100px);
  margin: 0;
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 1.5rem;
  align-items: start;
}

.controls-section {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  max-height: calc(100vh - 120px);
  overflow-y: auto;
  position: sticky;
  top: 0;
}

.upload-grid {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.error-banner {
  margin-top: 1rem;
  padding: 1rem;
  background: #fed7d7;
  color: #c53030;
  border-radius: 8px;
  border-left: 4px solid #e53e3e;
}

.data-status {
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e2e8f0;
}

.status-item {
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  border-radius: 8px;
  background: #f7fafc;
  color: #718096;
  transition: all 0.3s ease;
}

.status-item.active {
  background: #e6fffa;
  color: #234e52;
  border-left: 4px solid #38b2ac;
}

.chunk-info-mini {
  font-size: 0.75rem;
  color: #718096;
  font-weight: normal;
  margin-left: 0.5rem;
}

.chart-section {
  background: white;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  min-height: calc(100vh - 120px);
  display: flex;
  flex-direction: column;
}

.chart-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  width: 100%;
}

.placeholder-content {
  text-align: center;
  color: #718096;
}

.placeholder-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.placeholder-content h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.5rem;
  color: #4a5568;
}

.placeholder-content p {
  margin: 0;
  max-width: 400px;
}

/* Optimized for 1366x768 and similar resolutions */
@media (max-width: 1400px) and (min-width: 1200px) {
  .app-main {
    grid-template-columns: 320px 1fr;
    gap: 1.25rem;
  }
  
  .controls-section {
    padding: 1rem;
    max-height: calc(100vh - 100px);
  }
  
  .chart-section {
    min-height: calc(100vh - 100px);
    padding: 1rem;
    display: flex;
    flex-direction: column;
  }
}

@media (max-width: 1200px) {
  .app-main {
    grid-template-columns: 1fr;
    gap: 1.25rem;
    min-height: auto;
  }
  
  .controls-section {
    order: 2;
    max-height: none;
    position: static;
  }
  
  .chart-section {
    order: 1;
    min-height: 500px;
    display: flex;
    flex-direction: column;
  }
}

/* Specific optimizations for very low height screens */
@media (max-height: 800px) {
  .app-header {
    margin-bottom: 1rem;
  }
  
  .app-header h1 {
    font-size: 1.75rem;
    margin-bottom: 0.125rem;
  }
  
  .app-header p {
    font-size: 0.875rem;
  }
  
  .app-main {
    min-height: calc(100vh - 80px);
  }
  
  .controls-section {
    max-height: calc(100vh - 90px);
  }
  
  .chart-section {
    min-height: calc(100vh - 90px);
    display: flex;
    flex-direction: column;
  }
}

@media (max-width: 768px) {
  .app {
    padding: 0.5rem;
  }
  
  .app-header h1 {
    font-size: 1.5rem;
  }
  
  .app-header p {
    font-size: 0.875rem;
  }
  
  .app-main {
    min-height: calc(100vh - 70px);
  }
  
  .controls-section,
  .chart-section {
    padding: 0.75rem;
  }
}
</style>
