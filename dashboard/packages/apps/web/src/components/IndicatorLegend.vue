<script setup lang="ts">
import type { IndicatorSeries } from '../types/chart';

interface Props {
  indicators?: IndicatorSeries[];
  visible?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  visible: true
});

const emit = defineEmits<{
  toggleIndicator: [indicatorName: string];
  clearIndicators: [];
}>();
</script>

<template>
  <div v-if="indicators && indicators.length > 0 && props.visible" class="indicator-legend">
    <div class="legend-header">
      <h4>📈 Indicators Legend</h4>
      <button @click="emit('clearIndicators')" class="clear-btn" title="Clear all indicators">
        ✕
      </button>
    </div>
    
    <div class="legend-items">
      <div 
        v-for="indicator in indicators" 
        :key="indicator.name"
        class="legend-item"
        @click="emit('toggleIndicator', indicator.name)"
      >
        <div 
          class="color-indicator"
          :style="{ backgroundColor: indicator.color }"
        ></div>
        <span class="indicator-name">{{ indicator.name }}</span>
      </div>
    </div>
    
    <div class="legend-stats">
      <span class="stats-text">{{ indicators.length }} indicator{{ indicators.length === 1 ? '' : 's' }} loaded</span>
    </div>
  </div>
</template>

<style scoped>
.indicator-legend {
  background: #f8fafc;
  border-radius: 12px;
  padding: 1rem;
  border: 1px solid #e2e8f0;
  margin-bottom: 1rem;
  max-height: 300px;
  overflow-y: auto;
}

.legend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.legend-header h4 {
  margin: 0;
  color: #2d3748;
  font-size: 0.875rem;
  font-weight: 600;
}

.clear-btn {
  background: none;
  border: none;
  color: #e53e3e;
  cursor: pointer;
  font-size: 1.1rem;
  padding: 0.25rem;
  border-radius: 4px;
  transition: background-color 0.2s;
  line-height: 1;
}

.clear-btn:hover {
  background: rgba(229, 62, 62, 0.1);
}

.legend-items {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.5rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.legend-item:hover {
  background: #edf2f7;
}

.color-indicator {
  width: 16px;
  height: 3px;
  border-radius: 2px;
  flex-shrink: 0;
}

.indicator-name {
  font-size: 0.875rem;
  color: #2d3748;
  font-weight: 500;
  text-transform: capitalize;
  word-break: break-word;
}

.legend-stats {
  padding-top: 0.5rem;
  border-top: 1px solid #e2e8f0;
  text-align: center;
}

.stats-text {
  font-size: 0.75rem;
  color: #718096;
  font-style: italic;
}

/* Scrollbar styling for webkit browsers */
.indicator-legend::-webkit-scrollbar {
  width: 4px;
}

.indicator-legend::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 2px;
}

.indicator-legend::-webkit-scrollbar-thumb {
  background: #cbd5e0;
  border-radius: 2px;
}

.indicator-legend::-webkit-scrollbar-thumb:hover {
  background: #a0aec0;
}

@media (max-height: 800px) {
  .indicator-legend {
    max-height: 200px;
    padding: 0.75rem;
  }
  
  .legend-header h4 {
    font-size: 0.8rem;
  }
  
  .indicator-name {
    font-size: 0.8rem;
  }
  
  .legend-items {
    gap: 0.375rem;
  }
  
  .legend-item {
    padding: 0.25rem 0.375rem;
  }
}

@media (max-width: 768px) {
  .indicator-legend {
    padding: 0.5rem;
    max-height: 150px;
  }
  
  .legend-header h4 {
    font-size: 0.75rem;
  }
  
  .indicator-name {
    font-size: 0.75rem;
  }
  
  .color-indicator {
    width: 12px;
    height: 2px;
  }
}
</style>
