import apiClient from './client'

export interface FrontierTopic {
  id: string
  name: string
  source_type: string
  query: string
  knowledge_base_id: string
  knowledge_base_name: string
  cadence: string | null
  last_sync_at: string | null
  document_count: number
  indexed_count: number
}

export interface FrontierPaper {
  document_id: string
  title: string
  authors: string | null
  journal: string | null
  doi: string | null
  abstract: string | null
  publication_date: string | null
  created_at: string
  status: string
  knowledge_base_id: string
  knowledge_base_name: string
  source_type: string | null
  frontier_score: number
  relevance_score: number
  analysis_status: string | null
  analysis_risk_score: number | null
  risk_level: string | null
  reasons: string[]
  recommendation: string
}

export interface FrontierTrend {
  keyword: string
  count: number
}

export interface FocusPoint {
  id: string
  name: string
  query: string
  source_type: string
  max_results: number
  cron_expr: string | null
  knowledge_base_id: string | null
  knowledge_base_name: string | null
  sync_task_id: string | null
  sync_status: string | null
  last_message: string | null
  created_at: string
}

export interface FrontierResponse {
  topics: FrontierTopic[]
  papers: FrontierPaper[]
  trends: FrontierTrend[]
  total: number
}

export const frontierApi = {
  list: (params?: { topic_id?: string; kb_id?: string; days?: number; status?: string; limit?: number }) =>
    apiClient.get<FrontierResponse>('/frontier', { params }),
  listFocusPoints: () => apiClient.get<FocusPoint[]>('/frontier/focus-points'),
  createFocusPoint: (data: { name: string; query: string; source_type?: string; max_results?: number; cron_expr?: string; knowledge_base_id?: string; auto_sync?: boolean }) =>
    apiClient.post<FocusPoint>('/frontier/focus-points', data),
  deleteFocusPoint: (id: string) => apiClient.delete(`/frontier/focus-points/${id}`),
}
