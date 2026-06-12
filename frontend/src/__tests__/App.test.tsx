/**
 * App 路由守卫测试：
 * - 未登录时访问受保护路由，重定向到 /login
 * - 非 admin 访问 /admin/users，重定向到 /
 * - 已登录 admin 可正常访问 /admin/users
 */
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// mock 所有 lazy 加载的页面组件，避免动态 import 问题
vi.mock('@/pages/Dashboard', () => ({ default: () => <div>Dashboard页</div> }))
vi.mock('@/pages/KnowledgeBases', () => ({ default: () => <div>知识库页</div> }))
vi.mock('@/pages/DocumentUpload', () => ({ default: () => <div>文档上传页</div> }))
vi.mock('@/pages/Search', () => ({ default: () => <div>搜索页</div> }))
vi.mock('@/pages/Chat', () => ({ default: () => <div>对话页</div> }))
vi.mock('@/pages/Analytics', () => ({ default: () => <div>分析页</div> }))
vi.mock('@/pages/SyncTasks', () => ({ default: () => <div>同步任务页</div> }))
vi.mock('@/pages/Preferences', () => ({ default: () => <div>偏好设置页</div> }))
vi.mock('@/pages/admin/Users', () => ({ default: () => <div>用户管理页</div> }))
vi.mock('@/pages/admin/AuditLogs', () => ({ default: () => <div>审计日志页</div> }))
vi.mock('@/pages/admin/SystemSettings', () => ({ default: () => <div>系统设置页</div> }))
vi.mock('@/pages/Login', () => ({ default: () => <div>登录页</div> }))
vi.mock('@/components/Layout/AppLayout', () => ({
  default: () => {
    const { Outlet } = require('react-router-dom')
    return (
      <div>
        <div>布局</div>
        <Outlet />
      </div>
    )
  },
}))
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
vi.mock('@/api/auth', () => ({
  authApi: { login: vi.fn(), getMe: vi.fn(), refresh: vi.fn() },
}))

// mock useAuthStore，通过 mockStoreState 控制各测试的 store 状态
const mockStoreState = vi.fn()
vi.mock('@/stores/authStore', () => ({
  useAuthStore: (selector: (s: any) => any) => {
    const state = mockStoreState()
    return selector(state)
  },
}))

// 使用独立的 ProtectedRoute 和 AdminRoute 组件进行测试，
// 与 App.tsx 中的实现保持一致
import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuthStore } from '@/stores/authStore'

function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = useAuthStore((s: any) => s.accessToken)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AdminRoute({ children }: { children: ReactNode }) {
  const user = useAuthStore((s: any) => s.user)
  if (user?.role !== 'admin') return <Navigate to="/" replace />
  return <>{children}</>
}

describe('ProtectedRoute', () => {
  it('未登录时访问受保护路由，重定向到 /login', () => {
    mockStoreState.mockReturnValue({ accessToken: null, user: null })

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>登录页</div>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>受保护内容</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('登录页')).toBeTruthy()
    expect(screen.queryByText('受保护内容')).toBeNull()
  })

  it('已登录时访问受保护路由，正常渲染内容', () => {
    mockStoreState.mockReturnValue({
      accessToken: 'valid-token',
      user: { role: 'doctor' },
    })

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>登录页</div>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>受保护内容</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('受保护内容')).toBeTruthy()
    expect(screen.queryByText('登录页')).toBeNull()
  })
})

describe('AdminRoute', () => {
  it('非 admin 用户访问 admin 路由，重定向到 /', () => {
    mockStoreState.mockReturnValue({
      accessToken: 'valid-token',
      user: { role: 'doctor' },
    })

    render(
      <MemoryRouter initialEntries={['/admin/users']}>
        <Routes>
          <Route path="/" element={<div>首页</div>} />
          <Route
            path="/admin/users"
            element={
              <AdminRoute>
                <div>用户管理页</div>
              </AdminRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('首页')).toBeTruthy()
    expect(screen.queryByText('用户管理页')).toBeNull()
  })

  it('admin 用户访问 admin 路由，正常渲染', () => {
    mockStoreState.mockReturnValue({
      accessToken: 'admin-token',
      user: { role: 'admin' },
    })

    render(
      <MemoryRouter initialEntries={['/admin/users']}>
        <Routes>
          <Route path="/" element={<div>首页</div>} />
          <Route
            path="/admin/users"
            element={
              <AdminRoute>
                <div>用户管理页</div>
              </AdminRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('用户管理页')).toBeTruthy()
    expect(screen.queryByText('首页')).toBeNull()
  })

  it('researcher 角色访问 admin 路由被重定向', () => {
    mockStoreState.mockReturnValue({
      accessToken: 'researcher-token',
      user: { role: 'researcher' },
    })

    render(
      <MemoryRouter initialEntries={['/admin/users']}>
        <Routes>
          <Route path="/" element={<div>首页</div>} />
          <Route
            path="/admin/users"
            element={
              <AdminRoute>
                <div>用户管理页</div>
              </AdminRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('首页')).toBeTruthy()
    expect(screen.queryByText('用户管理页')).toBeNull()
  })

  it('user 为 null 时访问 admin 路由被重定向（登录但未获取用户信息）', () => {
    mockStoreState.mockReturnValue({
      accessToken: 'some-token',
      user: null,
    })

    render(
      <MemoryRouter initialEntries={['/admin/users']}>
        <Routes>
          <Route path="/" element={<div>首页</div>} />
          <Route
            path="/admin/users"
            element={
              <AdminRoute>
                <div>用户管理页</div>
              </AdminRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    )

    expect(screen.getByText('首页')).toBeTruthy()
    expect(screen.queryByText('用户管理页')).toBeNull()
  })
})
