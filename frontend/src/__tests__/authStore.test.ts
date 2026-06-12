/**
 * authStore 测试：login 设置 tokens 和 user，logout 清空状态。
 * 使用 vi.mock 隔离 API 调用，测试 store 状态变化。
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'

// mock API 模块，避免真实 HTTP 请求
vi.mock('@/api/auth', () => ({
  authApi: {
    login: vi.fn(),
    getMe: vi.fn(),
    refresh: vi.fn(),
  },
}))

// mock apiClient，避免 axios 初始化问题
vi.mock('@/api/client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}))

import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'

const mockUser = {
  id: 'user-uuid-123',
  username: 'testuser',
  email: 'test@example.com',
  full_name: '测试用户',
  role: 'doctor',
  department: '内科',
  is_active: true,
}

describe('authStore', () => {
  beforeEach(() => {
    // 每次测试前重置 store 状态
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      user: null,
    })
    vi.clearAllMocks()
  })

  describe('login', () => {
    it('登录成功后设置 accessToken、refreshToken 和 user', async () => {
      vi.mocked(authApi.login).mockResolvedValueOnce({
        data: { access_token: 'access-abc', refresh_token: 'refresh-xyz', token_type: 'bearer' },
      } as any)
      vi.mocked(authApi.getMe).mockResolvedValueOnce({
        data: mockUser,
      } as any)

      await useAuthStore.getState().login('testuser', 'pass123')

      const state = useAuthStore.getState()
      expect(state.accessToken).toBe('access-abc')
      expect(state.refreshToken).toBe('refresh-xyz')
      expect(state.user).toEqual(mockUser)
    })

    it('登录时 API 失败应抛出错误，不修改 store', async () => {
      vi.mocked(authApi.login).mockRejectedValueOnce(new Error('401 Unauthorized'))

      await expect(useAuthStore.getState().login('bad', 'wrong')).rejects.toThrow()

      const state = useAuthStore.getState()
      expect(state.accessToken).toBeNull()
      expect(state.user).toBeNull()
    })

    it('login 调用 authApi.login 传入正确参数', async () => {
      vi.mocked(authApi.login).mockResolvedValueOnce({
        data: { access_token: 'tok', refresh_token: 'ref', token_type: 'bearer' },
      } as any)
      vi.mocked(authApi.getMe).mockResolvedValueOnce({ data: mockUser } as any)

      await useAuthStore.getState().login('admin', 'admin123')

      expect(authApi.login).toHaveBeenCalledWith({ username: 'admin', password: 'admin123' })
    })

    it('login 成功后调用 getMe 获取用户信息', async () => {
      vi.mocked(authApi.login).mockResolvedValueOnce({
        data: { access_token: 'tok', refresh_token: 'ref', token_type: 'bearer' },
      } as any)
      vi.mocked(authApi.getMe).mockResolvedValueOnce({ data: mockUser } as any)

      await useAuthStore.getState().login('user', 'pass')

      expect(authApi.getMe).toHaveBeenCalledTimes(1)
    })
  })

  describe('logout', () => {
    it('logout 清空 accessToken、refreshToken 和 user', () => {
      useAuthStore.setState({
        accessToken: 'some-token',
        refreshToken: 'some-refresh',
        user: mockUser,
      })

      useAuthStore.getState().logout()

      const state = useAuthStore.getState()
      expect(state.accessToken).toBeNull()
      expect(state.refreshToken).toBeNull()
      expect(state.user).toBeNull()
    })

    it('logout 在未登录状态下调用不报错', () => {
      expect(() => useAuthStore.getState().logout()).not.toThrow()
    })
  })

  describe('setTokens', () => {
    it('setTokens 更新 accessToken 和 refreshToken', () => {
      useAuthStore.getState().setTokens('new-access', 'new-refresh')

      const state = useAuthStore.getState()
      expect(state.accessToken).toBe('new-access')
      expect(state.refreshToken).toBe('new-refresh')
    })
  })

  describe('fetchUser', () => {
    it('fetchUser 更新 user 状态', async () => {
      vi.mocked(authApi.getMe).mockResolvedValueOnce({ data: mockUser } as any)

      await useAuthStore.getState().fetchUser()

      expect(useAuthStore.getState().user).toEqual(mockUser)
    })
  })
})
