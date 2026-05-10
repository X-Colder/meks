import apiClient from './client'

export interface SearchParams {
  query: string
  knowledge_base_ids?: string[]
  top_k?: number
  min_score?: number
}

export interface SearchResultItem {
  document_id: string
  document_title: string
  chunk_content: string
  score: number
  page_number: number | null
  section_title: string | null
  authors: string | null
  journal: string | null
}

export interface SearchResponse {
  results: SearchResultItem[]
  query: string
  total: number
  duration_ms: number
}

export const searchApi = {
  semantic: (params: SearchParams) =>
    apiClient.post<SearchResponse>('/search/semantic', params),

  history: () => apiClient.get('/search/history'),
}
