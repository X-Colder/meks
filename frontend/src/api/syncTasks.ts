import apiClient from './client'

export interface SyncTask {
  id: string
  name: string
  source_type: string
  status: string
  config: Record<string, unknown>
  cron_expr: string | null
  target_kb_id: string
  processed_count: number
  total_count: number
  last_sync_at: string | null
  created_at: string
}

export interface SyncTaskListResponse {
  items: SyncTask[]
  total: number
  page: number
  page_size: number
}

export interface CreateSyncTaskParams {
  name: string
  source_type: string
  config: { query: string; max_results?: number }
  cron_expr?: string
  target_kb_id: string
}

export const syncTasksApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    apiClient.get<SyncTaskListResponse>('/sync-tasks', { params }),

  create: (data: CreateSyncTaskParams) =>
    apiClient.post<SyncTask>('/sync-tasks', data),

  run: (id: string) => apiClient.post(`/sync-tasks/${id}/run`),

  pause: (id: string) => apiClient.post(`/sync-tasks/${id}/pause`),

  delete: (id: string) => apiClient.delete(`/sync-tasks/${id}`),
}
