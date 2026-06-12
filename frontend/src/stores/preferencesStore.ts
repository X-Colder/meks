import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface PreferencesState {
  defaultTopK: number
  language: string
  setDefaultTopK: (val: number) => void
  setLanguage: (val: string) => void
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      defaultTopK: 10,
      language: 'zh',
      setDefaultTopK: (val) => set({ defaultTopK: val }),
      setLanguage: (val) => set({ language: val }),
    }),
    { name: 'meks-preferences' }
  )
)
