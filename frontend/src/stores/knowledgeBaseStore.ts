import { create } from 'zustand'
import { knowledgeBasesApi, KnowledgeBase } from '@/api/knowledgeBases'

interface KBState {
  kbs: KnowledgeBase[]
  loading: boolean
  lastFetched: number | null
  fetchKbs: () => Promise<void>
}

const CACHE_TTL = 30000 // 30s TTL，避免频繁请求

export const useKBStore = create<KBState>((set, get) => ({
  kbs: [],
  loading: false,
  lastFetched: null,

  fetchKbs: async () => {
    const { lastFetched, loading } = get()
    if (loading) return
    if (lastFetched && Date.now() - lastFetched < CACHE_TTL) return

    set({ loading: true })
    try {
      const res = await knowledgeBasesApi.list()
      set({ kbs: res.data, lastFetched: Date.now() })
    } finally {
      set({ loading: false })
    }
  },
}))
