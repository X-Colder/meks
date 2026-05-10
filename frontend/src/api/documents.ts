import apiClient from './client'

export interface DocumentItem {
  id: string
  title: string
  filename: string
  file_type: string
  file_size_bytes: number
  status: string
  authors: string | null
  journal: string | null
  doi: string | null
  chunk_count: number
  knowledge_base_id: string
  created_at: string
  error_message: string | null
}

export interface DocumentListResponse {
  items: DocumentItem[]
  total: number
  page: number
  page_size: number
}

export const documentsApi = {
  upload: (file: File, knowledgeBaseId: string, title?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('knowledge_base_id', knowledgeBaseId)
    if (title) formData.append('title', title)
    return apiClient.post<DocumentItem>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  list: (params?: { knowledge_base_id?: string; page?: number; page_size?: number }) =>
    apiClient.get<DocumentListResponse>('/documents', { params }),

  get: (id: string) => apiClient.get<DocumentItem>(`/documents/${id}`),

  delete: (id: string) => apiClient.delete(`/documents/${id}`),
}
