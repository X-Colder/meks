import apiClient from './client'

export interface AnalyticsQuery {
  query: string
  knowledge_base_ids?: string[]
}

export interface AnalyticsResponse {
  columns: string[]
  rows: Record<string, unknown>[]
  intent_type: string
  duration_ms: number
  total: number
}

export const analyticsApi = {
  query: (data: AnalyticsQuery) =>
    apiClient.post<AnalyticsResponse>('/analytics/query', data),
}
