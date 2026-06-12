import apiClient from './client'

export interface Paper {
  id: string
  title: string
  abstract: string | null
  status: string
  owner_id: string
  keywords: string | null
  target_journal: string | null
  created_at: string
  updated_at: string
}

export interface PaperBlock {
  id: string
  paper_id: string
  block_type: string
  content: string
  sort_order: number
  source_type: string | null
  source_id: string | null
  extra: string | null
  created_at: string
}

export interface PaperDetail extends Paper {
  blocks: PaperBlock[]
}

export const papersApi = {
  list: () => apiClient.get<Paper[]>('/papers'),
  create: (data: { title?: string }) => apiClient.post<Paper>('/papers', data),
  get: (id: string) => apiClient.get<PaperDetail>(`/papers/${id}`),
  update: (id: string, data: Partial<Paper>) => apiClient.patch<Paper>(`/papers/${id}`, data),
  delete: (id: string) => apiClient.delete(`/papers/${id}`),
  addBlock: (paperId: string, data: { block_type?: string; content: string; sort_order?: number; source_type?: string; source_id?: string; extra?: string }) =>
    apiClient.post<PaperBlock>(`/papers/${paperId}/blocks`, data),
  updateBlock: (paperId: string, blockId: string, data: Partial<PaperBlock>) =>
    apiClient.patch<PaperBlock>(`/papers/${paperId}/blocks/${blockId}`, data),
  deleteBlock: (paperId: string, blockId: string) =>
    apiClient.delete(`/papers/${paperId}/blocks/${blockId}`),
  reorderBlocks: (paperId: string, blockIds: string[]) =>
    apiClient.post(`/papers/${paperId}/blocks/reorder`, { block_ids: blockIds }),
  importContent: (paperId: string, data: { source_type: string; source_id?: string; content: string; block_type?: string }) =>
    apiClient.post<PaperBlock>(`/papers/${paperId}/import`, data),
  exportWord: (paperId: string, watermarkText?: string) =>
    apiClient.post(`/papers/${paperId}/export/word`, { watermark_text: watermarkText || null }, { responseType: 'blob' }),
  exportPdf: (paperId: string, watermarkText?: string) =>
    apiClient.post(`/papers/${paperId}/export/pdf`, { watermark_text: watermarkText || null }, { responseType: 'blob' }),
}
