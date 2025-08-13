<template>
  <div class="file-upload">
    <div class="upload-area" @click="triggerFileInput" @dragover.prevent @drop.prevent="handleDrop">
      <input
        ref="fileInput"
        type="file"
        accept=".csv"
        @change="handleFileSelect"
        style="display: none"
      />
      
      <div class="upload-content">
        <div class="upload-icon">📁</div>
        <div class="upload-text">
          <h3>{{ title }}</h3>
          <p>Click to browse or drag and drop a CSV file</p>
          <p class="file-info" v-if="description">{{ description }}</p>
        </div>
      </div>
      
      <div v-if="loading" class="loading-overlay">
        <div class="spinner"></div>
        <p>Processing file...</p>
      </div>
    </div>
    
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
    
    <div v-if="fileName" class="file-status">
      <span class="file-name">📄 {{ fileName }}</span>
      <button @click="clearFile" class="clear-btn">✕</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

interface Props {
  title: string;
  description?: string;
  loading?: boolean;
}

interface Emits {
  (e: 'file-selected', file: File): void;
  (e: 'file-cleared'): void;
}

defineProps<Props>();
const emit = defineEmits<Emits>();

const fileInput = ref<HTMLInputElement>();
const fileName = ref<string>('');
const error = ref<string>('');

const triggerFileInput = () => {
  fileInput.value?.click();
};

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (file) {
    processFile(file);
  }
};

const handleDrop = (event: DragEvent) => {
  const file = event.dataTransfer?.files?.[0];
  if (file) {
    processFile(file);
  }
};

const processFile = (file: File) => {
  error.value = '';
  
  if (!file.name.toLowerCase().endsWith('.csv')) {
    error.value = 'Please select a CSV file';
    return;
  }
  
  fileName.value = file.name;
  emit('file-selected', file);
};

const clearFile = () => {
  fileName.value = '';
  error.value = '';
  if (fileInput.value) {
    fileInput.value.value = '';
  }
  emit('file-cleared');
};
</script>

<style scoped>
.file-upload {
  margin-bottom: 1.5rem;
}

.upload-area {
  border: 2px dashed #4a5568;
  border-radius: 12px;
  padding: 1.5rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #f7fafc;
  position: relative;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-area:hover {
  border-color: #667eea;
  background: #edf2f7;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}

.upload-icon {
  font-size: 2.5rem;
  opacity: 0.7;
}

.upload-text h3 {
  margin: 0;
  font-size: 1.25rem;
  color: #2d3748;
  font-weight: 600;
}

.upload-text p {
  margin: 0.5rem 0 0 0;
  color: #718096;
  font-size: 0.875rem;
}

.file-info {
  font-style: italic;
  color: #4a5568 !important;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #fed7d7;
  color: #c53030;
  border-radius: 8px;
  font-size: 0.875rem;
}

.file-status {
  margin-top: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem;
  background: #e6fffa;
  border: 1px solid #81e6d9;
  border-radius: 8px;
}

.file-name {
  color: #234e52;
  font-weight: 500;
}

.clear-btn {
  background: none;
  border: none;
  color: #e53e3e;
  cursor: pointer;
  font-size: 1.2rem;
  padding: 0.25rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.clear-btn:hover {
  background: rgba(229, 62, 62, 0.1);
}

@media (max-height: 800px) {
  .file-upload {
    margin-bottom: 1rem;
  }
  
  .upload-area {
    padding: 1rem;
    min-height: 100px;
  }
  
  .upload-content {
    gap: 0.75rem;
  }
  
  .upload-icon {
    font-size: 2rem;
  }
  
  .upload-text h3 {
    font-size: 1.125rem;
  }
  
  .upload-text p {
    font-size: 0.8rem;
  }
}

@media (max-width: 768px) {
  .upload-area {
    padding: 0.75rem;
    min-height: 80px;
  }
  
  .upload-icon {
    font-size: 1.75rem;
  }
  
  .upload-text h3 {
    font-size: 1rem;
  }
  
  .upload-text p {
    font-size: 0.75rem;
  }
}
</style>
