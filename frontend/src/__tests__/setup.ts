import '@testing-library/jest-dom'

// 模拟 window.location 避免 JSDOM 导航错误
Object.defineProperty(window, 'location', {
  value: { href: '/', assign: vi.fn(), replace: vi.fn() },
  writable: true,
})

// 模拟 localStorage（zustand persist 需要）
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value },
    removeItem: (key: string) => { delete store[key] },
    clear: () => { store = {} },
  }
})()
Object.defineProperty(window, 'localStorage', { value: localStorageMock })
