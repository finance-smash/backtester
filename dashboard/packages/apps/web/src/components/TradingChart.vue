<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue';
import { 
  createChart, 
  type IChartApi, 
  type ISeriesApi,
  CandlestickSeries,
  HistogramSeries,
  LineSeries,
  createSeriesMarkers,
  createTextWatermark,
  ColorType, 
  type Time, 
  type ISeriesMarkersPluginApi
} from 'lightweight-charts';
import type { ChartCandle, ParsedOrder, OrderMarker, ParsedIndicator, IndicatorSeries } from '../types/chart';
import { formatGMTTime } from '../utils/timeUtils';
import { generateIndicatorColorMap } from '../utils/colorUtils';

interface Props {
  candles?: ChartCandle[];
  orders?: ParsedOrder[];
  indicators?: ParsedIndicator[];
  chunkStartIndex?: number; // Global index where this chunk starts
  chunkEndIndex?: number;   // Global index where this chunk ends
}

const props = defineProps<Props>();

const validCandlesComputed = computed(() => (
props.candles?.filter(candle => 
candle.time && 
!isNaN(candle.time) && 
!isNaN(candle.open) && 
!isNaN(candle.high) && 
!isNaN(candle.low) && 
!isNaN(candle.close) && 
!isNaN(candle.volume)
) || []
));

const sortedCandlesComputed = computed(() => (
validCandlesComputed.value.sort((a, b) => a.time - b.time)
.filter((candle, index, array) => {
  // Keep only the first occurrence of each timestamp
  return index === 0 || candle.time !== array[index - 1].time;
})
))

const emit = defineEmits<{
  indicatorsLoaded: [indicators: IndicatorSeries[]];
}>();

const chartContainer = ref<HTMLDivElement>();
let chart: IChartApi | null = null;
let candlestickSeries: ISeriesApi<'Candlestick'> | null = null;
let markersSeries: ISeriesMarkersPluginApi<Time> | null = null;
  let volumeSeries: ISeriesApi<'Histogram'> | null = null;
  const indicatorSeriesMap: Map<string, ISeriesApi<'Line'>> = new Map();
  const indicatorSeries = ref<IndicatorSeries[]>([]);
  
  const initChart = async () => {
    if (!chartContainer.value) return;
    
    chart = createChart(chartContainer.value, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: '#1e1e1e' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2a2a2a' },
        horzLines: { color: '#2a2a2a' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#2a2a2a',
      },
      timeScale: {
        borderColor: '#2a2a2a',
        timeVisible: true,
        secondsVisible: false,
        // Ensure times are displayed in UTC/GMT
        shiftVisibleRangeOnNewBar: true,
      },
      // Configure localization to use UTC
      localization: {
        timeFormatter: (time: number) => {
          // Use the dedicated GMT time formatter
          return formatGMTTime(time, false); // Don't include seconds in the chart display
        },
        priceFormatter: (price: number) => {
          return price.toFixed(2);
        },
      },
    });
    
    // Create candlestick series using v5 API
    candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#4bffb5',
      downColor: '#ff4976',
      borderDownColor: '#ff4976',
      borderUpColor: '#4bffb5',
      wickDownColor: '#ff4976',
      wickUpColor: '#4bffb5',
    });
    
    // Create volume series using v5 API
    volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume',
    });
    
    // Configure volume price scale
    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });
    
    // Add watermark using v5 API
    const firstPane = chart.panes()[0];
    createTextWatermark(firstPane, {
      horzAlign: 'center',
      vertAlign: 'center',
      lines: [
      {
        text: 'Trading Dashboard',
        color: 'rgba(255, 255, 255, 0.1)',
        fontSize: 24,
      },
      {
        text: 'Times displayed in GMT',
        color: 'rgba(255, 255, 255, 0.08)',
        fontSize: 12,
      }
      ],
    });
    
    await loadCandles();
    await loadOrders();
    await loadIndicators();
  };
  
  const loadCandles = async () => {
    if (!props.candles || !candlestickSeries || !volumeSeries) return;
    
    try {
      // Filter out invalid candles and sort by time in ascending order (required by TradingView)
      const validCandles = props.candles.filter(candle => 
      candle.time && 
      !isNaN(candle.time) && 
      !isNaN(candle.open) && 
      !isNaN(candle.high) && 
      !isNaN(candle.low) && 
      !isNaN(candle.close) && 
      !isNaN(candle.volume)
      );
      
      // Sort by time and remove duplicates (TradingView requires unique timestamps)
      const sortedCandles = [...validCandles]
      .sort((a, b) => a.time - b.time)
      .filter((candle, index, array) => {
        // Keep only the first occurrence of each timestamp
        return index === 0 || candle.time !== array[index - 1].time;
      });
      
      if (sortedCandles.length === 0) {
        console.warn('No valid candle data to display');
        return;
      }
      
      console.log(`Chunk loaded: ${validCandles.length} valid candles, ${sortedCandles.length} unique candles after deduplication`);
      
      // Set candlestick data with proper time type casting
      const candleData = sortedCandles.map(candle => ({
        time: candle.time as Time,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      }));
      candlestickSeries.setData(candleData);
      
      // Set volume data with proper time type casting
      const volumeData = sortedCandles.map(candle => ({
        time: candle.time as Time,
        value: candle.volume,
        color: candle.close >= candle.open ? '#4bffb5' : '#ff4976',
      }));
      volumeSeries.setData(volumeData);
      
      // Fit content to show the current chunk properly
      chart?.timeScale().fitContent();
    } catch (error) {
      console.error('Error loading candles:', error);
    }
  };
  
  const loadOrders = async () => {
    if (!props.orders || !props.candles || !candlestickSeries) return;
    
    try {
      // Use the same validation and sorting logic as in loadCandles
      
      // Sort by time and remove duplicates (same as loadCandles)
      const sortedCandles = sortedCandlesComputed.value;
      
      if (sortedCandles.length === 0) {
        console.warn('No valid candle data for order markers');
        return;
      }
      
      console.log('chunkStartIndex', props.chunkStartIndex);
      console.log('chunkEndIndex', props.chunkEndIndex);
      
      // Debug logging for chunk-based order mapping
      if (props.chunkStartIndex !== undefined && props.chunkEndIndex !== undefined) {
        console.log(`🔍 Loading orders for chunk: rows ${props.chunkStartIndex}-${props.chunkEndIndex}`);
        console.log(`📊 Total orders: ${props.orders.length}, Available candles in chunk: ${sortedCandles.length}`);
        
        const ordersInChunk = props.orders.filter(order => {
          const globalIndex = Math.floor(order.candle_index);
          return globalIndex >= props.chunkStartIndex! && globalIndex < props.chunkEndIndex!;
        });
        console.log(`📈 Orders belonging to this chunk: ${ordersInChunk.length}`);
        
        // Log first few candles to understand the data structure
        if (sortedCandles.length > 0) {
          console.log(`🕐 First candle time: ${formatGMTTime(sortedCandles[0].time)}`);
          console.log(`🕕 Last candle time: ${formatGMTTime(sortedCandles[sortedCandles.length - 1].time)}`);
        }
        
        // Log first few orders in chunk
        ordersInChunk.slice(0, 3).forEach((order, i) => {
          const relativeIndex = Math.floor(order.candle_index) - props.chunkStartIndex!;
          console.log(`📋 Order ${i + 1}: candle_index=${order.candle_index}, relative_index=${relativeIndex}, price=${order.price}`);
        });
      }
      
      const orderMarkers: OrderMarker[] = props.orders.map(order => {
        const originalCandleIndex = Math.floor(order.candle_index);
        
        // If we have chunk information, check if this order belongs to the current chunk
        if (props.chunkStartIndex !== undefined && props.chunkEndIndex !== undefined) {
          // Check if the order's original candle index falls within the current chunk range
          if (originalCandleIndex < props.chunkStartIndex || originalCandleIndex >= props.chunkEndIndex) {
            return null; // Order doesn't belong to this chunk
          }
          
          // CORE FIX: The issue is that we need to account for the fact that
          // sortedCandles might have fewer items than the chunk size due to filtering/deduplication
          // So we can't use simple arithmetic. Instead, we need to understand that
          // sortedCandles[0] corresponds to chunkStartIndex, sortedCandles[1] to chunkStartIndex+1, etc.
          // BUT only for the valid, non-duplicate candles
          
          const relativeIndex = originalCandleIndex - props.chunkStartIndex;
          
          // Since sortedCandles is the processed version of the chunk data,
          // and filtering/sorting might have changed the count, we need to be more careful
          if (relativeIndex < 0 || relativeIndex >= sortedCandles.length) {
            console.log(`🔍 Order candle_index ${originalCandleIndex} -> relative ${relativeIndex}, but chunk only has ${sortedCandles.length} candles after processing`);
            return null;
          }
          
          const candle = sortedCandles[relativeIndex];
          
          console.log(`✅ Order at global index ${originalCandleIndex} -> chunk relative ${relativeIndex} -> candle time ${formatGMTTime(candle.time)}`);
          
          console.log(JSON.parse(JSON.stringify(order)));
          
          return createOrderMarker(order, candle);
        } else {
          // Traditional mode: direct index mapping
          if (originalCandleIndex < 0 || originalCandleIndex >= sortedCandles.length) {
            return null;
          }
          
          const candle = sortedCandles[originalCandleIndex];
          return createOrderMarker(order, candle);
        }
      }).filter((marker): marker is OrderMarker => marker !== null);
      
      // Helper function to create order markers
      function createOrderMarker(order: ParsedOrder, candle: ChartCandle): OrderMarker {
        const isBuy = order.side === 1;
        const isOpen = order.offset === 1;
        
        let color = '#ffffff';
        let shape: 'circle' | 'square' | 'arrow' = 'circle';
        let text = '';
        
        if (isOpen) {
          color = isBuy ? '#4bffb5' : '#ff4976';
          shape = 'arrow';
          text = isBuy ? 'BUY' : 'SELL';
        } else {
          color = '#ffa726';
          shape = 'square';
          text = 'CLOSE';
        }
        
        return {
          time: candle.time,
          position: isBuy ? 'below' : 'above',
          color,
          shape,
          text: `${text} $${order.price.toFixed(2)}`,
          size: 'normal'
        } as OrderMarker;
      }
      
      // Create markers for the chart using v5 API
      const markers = orderMarkers.map(marker => ({
        time: marker.time as Time,
        position: marker.position === 'above' ? 'aboveBar' as const : 'belowBar' as const,
        color: marker.color,
        shape: marker.shape === 'arrow' ? 'arrowUp' as const : marker.shape === 'square' ? 'square' as const : 'circle' as const,
        text: marker.text,
        size: 1,
      }));

      console.log("markers", markers);
      
      if (markersSeries) {
        console.log("setting markers", markers);
        markersSeries.setMarkers(markers);
      } else {
        console.log("creating markers", markers);
        markersSeries = createSeriesMarkers(candlestickSeries, markers);
      }
      
    } catch (error) {
      console.error('Error loading orders:', error);
    }
  };
  
  const loadIndicators = async () => {
    if (!props.indicators || !props.candles || !chart) return;
    
    try {
      // Clear existing indicator series
      indicatorSeriesMap.forEach((series, _name) => {
        chart!.removeSeries(series);
      });
      indicatorSeriesMap.clear();
      indicatorSeries.value = [];
      
      // Sort by time and remove duplicates (same as loadCandles)
      const sortedCandles = sortedCandlesComputed.value;
      
      if (sortedCandles.length === 0) {
        console.warn('No valid candle data for indicators');
        return;
      }
      
      // Get all indicator names from the first indicator row
      const indicatorNames = props.indicators.length > 0 ? Object.keys(props.indicators[0]) : [];
      
      if (indicatorNames.length === 0) {
        console.warn('No indicator columns found');
        return;
      }
      
      // Generate colors for indicators
      const colorMap = generateIndicatorColorMap(indicatorNames);
      
      console.log(`Loading indicators: ${indicatorNames.join(', ')}`);
      console.log(`Chunk info - Start: ${props.chunkStartIndex}, End: ${props.chunkEndIndex}, Candles: ${sortedCandles.length}, Total indicators: ${props.indicators.length}`);
      
      // Process each indicator
      for (const indicatorName of indicatorNames) {
        const indicatorData: Array<{ time: number; value: number }> = [];
        
        // Match indicators to candles considering chunk mode
        if (props.chunkStartIndex !== undefined && props.chunkEndIndex !== undefined) {
          // In chunk mode: map global indicator indices to local candle indices
          for (let i = 0; i < sortedCandles.length; i++) {
            const globalIndex = props.chunkStartIndex + i;
            
            // Make sure we don't exceed the indicators array bounds
            if (globalIndex < props.indicators.length) {
              const candle = sortedCandles[i];
              const indicatorRow = props.indicators[globalIndex];
              const value = indicatorRow[indicatorName];
              
              // Only add valid (non-null, non-NaN) values
              if (value !== null && value !== undefined && !isNaN(value)) {
                indicatorData.push({
                  time: candle.time,
                  value: value
                });
              }
            }
          }
          
          console.log(`Chunk mode: Indicator "${indicatorName}" - chunk start: ${props.chunkStartIndex}, mapped ${indicatorData.length} points`);
        } else {
          // Traditional mode: direct index mapping
          for (let i = 0; i < Math.min(sortedCandles.length, props.indicators.length); i++) {
            const candle = sortedCandles[i];
            const indicatorRow = props.indicators[i];
            const value = indicatorRow[indicatorName];
            
            // Only add valid (non-null, non-NaN) values
            if (value !== null && value !== undefined && !isNaN(value)) {
              indicatorData.push({
                time: candle.time,
                value: value
              });
            }
          }
          
          console.log(`Traditional mode: Indicator "${indicatorName}" - mapped ${indicatorData.length} points`);
        }
        
        // Only create series if we have data points
        if (indicatorData.length > 0) {
          const color = colorMap.get(indicatorName) || '#ffffff';
          
          // Create line series for this indicator
          const lineSeries = chart.addSeries(LineSeries, {
            color: color,
            lineWidth: 2,
            title: indicatorName,
            priceLineVisible: false,
            lastValueVisible: true,
          });
          
          // Set data for the line series
          lineSeries.setData(indicatorData.map(point => ({
            time: point.time as Time,
            value: point.value
          })));
          
          // Store the series reference
          indicatorSeriesMap.set(indicatorName, lineSeries);
          
          // Add to reactive indicator series for legend
          indicatorSeries.value.push({
            name: indicatorName,
            data: indicatorData,
            color: color
          });
          
          console.log(`Added indicator "${indicatorName}" with ${indicatorData.length} data points (color: ${color})`);
        } else {
          console.warn(`No valid data points for indicator "${indicatorName}"`);
        }
      }
      
      console.log(`Successfully loaded ${indicatorSeries.value.length} indicators`);
      
      // Emit the loaded indicators to parent component
      emit('indicatorsLoaded', indicatorSeries.value);
    } catch (error) {
      console.error('Error loading indicators:', error);
    }
  };
  
  const resizeChart = () => {
    if (chart && chartContainer.value) {
      const rect = chartContainer.value.getBoundingClientRect();
      chart.applyOptions({
        width: rect.width,
        height: rect.height,
      });
    }
  };
  
  // Watch for props changes
  watch(() => props.candles, async () => {
    await loadCandles();
    // Trigger resize after data is loaded
    setTimeout(resizeChart, 100);
  }, { deep: true });
  
  watch([() => props.indicators, () => props.chunkStartIndex, () => props.chunkEndIndex, () => props.orders], async () => {
    await loadIndicators();
    await loadOrders(); // Reload orders after indicators to ensure markers are displayed
  }, { deep: true });
  
  onMounted(async () => {
    await nextTick();
    await initChart();
    
    // Initial resize after chart creation
    setTimeout(resizeChart, 100);
    
    window.addEventListener('resize', resizeChart);
  });
  
  onUnmounted(() => {
    window.removeEventListener('resize', resizeChart);
    
    // Clear indicator series
    indicatorSeriesMap.forEach((series) => {
      if (chart) {
        chart.removeSeries(series);
      }
    });
    indicatorSeriesMap.clear();
    
    if (chart) {
      chart.remove();
    }
  });
</script>

<template>
  <div class="trading-chart">
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<style scoped>
.trading-chart {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
}

.chart-container {
  width: 100%;
  flex: 1;
  min-height: 400px;
  border-radius: 8px;
  overflow: hidden;
  background: #1e1e1e;
}

@media (max-height: 800px) {
  .chart-container {
    min-height: 350px;
  }
}

@media (max-height: 600px) {
  .chart-container {
    min-height: 300px;
  }
}
</style>
