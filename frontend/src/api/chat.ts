import apiClient from './client'

export interface ChatSession {
  id: string
  title: string
  knowledge_base_ids: string
  message_count: number
  created_at: string
}

export interface ChatMessage {
  id: string
  role: string
  content: string
  source_chunks: string | null
  llm_provider: string | null
  model_name: string | null
  created_at: string
}

export const chatApi = {
  createSession: (data: { title?: string; knowledge_base_ids: string[] }) =>
    apiClient.post<ChatSession>('/chat/sessions', data),

  listSessions: () => apiClient.get<ChatSession[]>('/chat/sessions'),

  getMessages: (sessionId: string) =>
    apiClient.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`),

  deleteSession: (sessionId: string) =>
    apiClient.delete(`/chat/sessions/${sessionId}`),
}
