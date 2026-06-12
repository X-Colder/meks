import apiClient from './client'

export interface ModelInfo {
  name: string
  type: string
  status: string
}

export interface StorageStats {
  minio: { bucket_count: number; total_size: string }
  postgres: { total_rows: number; tables: Record<string, number> }
  milvus: { collection_count: number; total_vectors: number }
}

export interface HealthStatus {
  service: string
  status: 'healthy' | 'unhealthy' | 'degraded'
  latency_ms: number
}

export const systemApi = {
  getModels: () => apiClient.get<ModelInfo[]>('/admin/system/models'),

  getStorage: () => apiClient.get<StorageStats>('/admin/system/storage'),

  getHealth: () => apiClient.get<HealthStatus[]>('/admin/system/health'),
}
