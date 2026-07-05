import apiClient from './client'

export interface ReadingCard {
  id: string
  document_id: string
  content: string
  generated_by: string | null
  created_at: string
  updated_at: string
}

export const readingCardsApi = {
  get: (documentId: string) => apiClient.get<ReadingCard>(`/reading-cards/${documentId}`),
  save: (documentId: string, content: string) =>
    apiClient.put<ReadingCard>(`/reading-cards/${documentId}`, { content }),
  generate: (documentId: string) => apiClient.post(`/reading-cards/${documentId}/generate`),
}
