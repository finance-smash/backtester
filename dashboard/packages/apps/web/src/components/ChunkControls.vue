<script setup lang="ts">
interface ChunkMetadata {
  totalChunks: number;
  chunkSize: number;
  totalRows: number;
}

interface Props {
  chunkMetadata?: ChunkMetadata;
  currentChunk?: number;
  loading?: boolean;
  showMemoryInfo?: boolean;
  ordersInChunk?: number;
}

const props = withDefaults(defineProps<Props>(), {
  currentChunk: 0,
  loading: false,
  showMemoryInfo: true
});

const emit = defineEmits<{
  goToFirstChunk: [];
  goToPreviousChunk: [];
  goToNextChunk: [];
  goToLastChunk: [];
  goToChunk: [chunkIndex: number];
  changeChunkSize: [newSize: number];
}>();

const getChunkStartRow = (): number => {
  if (!props.chunkMetadata) return 0;
  return props.currentChunk * props.chunkMetadata.chunkSize;
};

const getChunkEndRow = (): number => {
  if (!props.chunkMetadata) return 0;
  const start = getChunkStartRow();
  return Math.min(start + props.chunkMetadata.chunkSize, props.chunkMetadata.totalRows);
};

const handleSliderChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const chunkIndex = parseInt(target.value);
  emit('goToChunk', chunkIndex);
};

const handleChunkSizeChange = (event: Event) => {
  const target = event.target as HTMLSelectElement;
  const newSize = parseInt(target.value);
  emit('changeChunkSize', newSize);
};
</script>

<template>
  <div class="chunk-controls">
    <div class="chunk-info" v-if="chunkMetadata">
      <h3>📊 Chunk Navigation</h3>
      <div class="chunk-stats">
        <div class="stat-item">
          <span class="stat-label">Total Rows:</span>
          <span class="stat-value">{{ chunkMetadata.totalRows.toLocaleString() }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Chunk Size:</span>
          <span class="stat-value">{{ chunkMetadata.chunkSize.toLocaleString() }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Total Chunks:</span>
          <span class="stat-value">{{ chunkMetadata.totalChunks }}</span>
        </div>
      </div>
    </div>

    <div class="chunk-navigation" v-if="chunkMetadata && currentChunk !== null">
      <div class="current-chunk-info">
        <div class="chunk-indicator">
          Chunk {{ currentChunk + 1 }} of {{ chunkMetadata.totalChunks }}
        </div>
        <div class="chunk-range">
          Rows {{ getChunkStartRow() + 1 }}-{{ getChunkEndRow() }}
        </div>
        <div v-if="ordersInChunk !== undefined" class="orders-in-chunk">
          📈 {{ ordersInChunk }} orders in this chunk
        </div>
      </div>

      <div class="navigation-buttons">
        <button 
          @click="$emit('goToFirstChunk')"
          :disabled="currentChunk === 0 || loading"
          class="nav-button first"
          title="Go to first chunk"
        >
          ⏮️
        </button>
        
        <button 
          @click="$emit('goToPreviousChunk')"
          :disabled="currentChunk === 0 || loading"
          class="nav-button prev"
          title="Previous chunk"
        >
          ⏪
        </button>
        
        <button 
          @click="$emit('goToNextChunk')"
          :disabled="currentChunk >= chunkMetadata.totalChunks - 1 || loading"
          class="nav-button next"
          title="Next chunk"
        >
          ⏩
        </button>
        
        <button 
          @click="$emit('goToLastChunk')"
          :disabled="currentChunk >= chunkMetadata.totalChunks - 1 || loading"
          class="nav-button last"
          title="Go to last chunk"
        >
          ⏭️
        </button>
      </div>

      <div class="chunk-slider">
        <input
          type="range"
          :min="0"
          :max="chunkMetadata.totalChunks - 1"
          :value="currentChunk"
          @input="handleSliderChange"
          :disabled="loading"
          class="slider"
        />
      </div>

      <div class="chunk-size-controls">
        <label for="chunk-size">Chunk Size:</label>
        <select 
          id="chunk-size"
          :value="chunkMetadata.chunkSize"
          @change="handleChunkSizeChange"
          :disabled="loading"
          class="chunk-size-select"
        >
          <option value="500">500 rows</option>
          <option value="1000">1,000 rows</option>
          <option value="2000">2,000 rows</option>
          <option value="5000">5,000 rows</option>
          <option value="10000">10,000 rows</option>
        </select>
      </div>
    </div>

    <div class="loading-indicator" v-if="loading">
      <div class="spinner"></div>
      <span>Loading chunk...</span>
    </div>

    <div class="memory-info" v-if="showMemoryInfo">
      <div class="memory-tip">
        💡 <strong>Memory Optimization:</strong> Only one chunk is loaded at a time to keep the browser responsive with large datasets.
      </div>
    </div>
  </div>
</template>

<style scoped>
.chunk-controls {
  background: #f8fafc;
  border-radius: 12px;
  padding: 1.25rem;
  border: 1px solid #e2e8f0;
  margin-bottom: 1rem;
}

.chunk-info h3 {
  margin: 0 0 1rem 0;
  color: #2d3748;
  font-size: 1rem;
  font-weight: 600;
}

.chunk-stats {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid #e2e8f0;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  color: #718096;
  font-size: 0.875rem;
  font-weight: 500;
}

.stat-value {
  color: #2d3748;
  font-weight: 600;
  font-size: 0.875rem;
}

.chunk-navigation {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.current-chunk-info {
  text-align: center;
  padding: 0.75rem;
  background: white;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.chunk-indicator {
  font-weight: 600;
  color: #2d3748;
  font-size: 0.875rem;
  margin-bottom: 0.25rem;
}

.chunk-range {
  color: #718096;
  font-size: 0.75rem;
}

.orders-in-chunk {
  color: #667eea;
  font-size: 0.75rem;
  margin-top: 0.25rem;
  font-weight: 500;
}

.navigation-buttons {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
}

.nav-button {
  padding: 0.5rem;
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 1rem;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-button:hover:not(:disabled) {
  background: #f7fafc;
  border-color: #cbd5e0;
}

.nav-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chunk-slider {
  padding: 0.5rem 0;
}

.slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.slider::-moz-range-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #667eea;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.chunk-size-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;
}

.chunk-size-controls label {
  font-size: 0.875rem;
  color: #718096;
  font-weight: 500;
}

.chunk-size-select {
  padding: 0.375rem 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  background: white;
  font-size: 0.875rem;
  color: #2d3748;
  cursor: pointer;
}

.chunk-size-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.loading-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 1rem;
  color: #718096;
  font-size: 0.875rem;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #e2e8f0;
  border-top: 2px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.memory-info {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.memory-tip {
  background: #e6fffa;
  color: #234e52;
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 0.875rem;
  line-height: 1.4;
  border-left: 3px solid #38b2ac;
}
</style>
