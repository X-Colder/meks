import apiClient from './client'

export interface KnowledgeBase {
  id: string
  name: string
  description: string | null
  visibility: string
  department: string | null
  document_count: number
  owner_id: string
  created_at: string
}

export const knowledgeBasesApi = {
  list: () => apiClient.get<KnowledgeBase[]>('/knowledge-bases'),

  get: (id: string) => apiClient.get<KnowledgeBase>(`/knowledge-bases/${id}`),

  create: (data: { name: string; description?: string; visibility?: string }) =>
    apiClient.post<KnowledgeBase>('/knowledge-bases', data),

  update: (id: string, data: Partial<{ name: string; description: string; visibility: string }>) =>
    apiClient.patch<KnowledgeBase>(`/knowledge-bases/${id}`, data),

  delete: (id: string) => apiClient.delete(`/knowledge-bases/${id}`),
}
