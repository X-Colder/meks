import { lazy, Suspense, Component, ReactNode, useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Spin, Result, Button } from 'antd'
import { useAuthStore } from '@/stores/authStore'
import AppLayout from '@/components/Layout/AppLayout'
import Login from '@/pages/Login'

// 代码分割：lazy 加载页面组件
const Dashboard = lazy(() => import('@/pages/Dashboard'))
const KnowledgeBases = lazy(() => import('@/pages/KnowledgeBases'))
const DocumentUpload = lazy(() => import('@/pages/DocumentUpload'))
const Search = lazy(() => import('@/pages/Search'))
const Chat = lazy(() => import('@/pages/Chat'))
const Analytics = lazy(() => import('@/pages/Analytics'))
const SyncTasks = lazy(() => import('@/pages/SyncTasks'))
const FrontierDiscovery = lazy(() => import('@/pages/FrontierDiscovery'))
const LiteratureReading = lazy(() => import('@/pages/LiteratureReading'))
const ResearchDesign = lazy(() => import('@/pages/ResearchDesign'))
const GrantMaterials = lazy(() => import('@/pages/GrantMaterials'))
const Preferences = lazy(() => import('@/pages/Preferences'))
const PaperAnalysis = lazy(() => import('@/pages/PaperAnalysis'))
const PaperEditor = lazy(() => import('@/pages/PaperEditor'))
const Users = lazy(() => import('@/pages/admin/Users'))
const AuditLogs = lazy(() => import('@/pages/admin/AuditLogs'))
const SystemSettings = lazy(() => import('@/pages/admin/SystemSettings'))

class ErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="页面出错了"
          subTitle="请刷新页面重试"
          extra={
            <Button type="primary" onClick={() => window.location.reload()}>
              刷新页面
            </Button>
          }
        />
      )
    }
    return this.props.children
  }
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const token = useAuthStore((s) => s.accessToken)
  const user = useAuthStore((s) => s.user)
  const fetchUser = useAuthStore((s) => s.fetchUser)
  const [checking, setChecking] = useState(false)

  useEffect(() => {
    if (token && !user && !checking) {
      setChecking(true)
      fetchUser().finally(() => setChecking(false))
    }
  }, [token, user, checking, fetchUser])

  if (!token) return <Navigate to="/login" replace />
  if (!user && checking) return PageLoader
  return <>{children}</>
}

function AdminRoute({ children }: { children: ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (user?.role !== 'admin') return <Navigate to="/" replace />
  return <>{children}</>
}

const PageLoader = (
  <div style={{ display: 'flex', justifyContent: 'center', padding: 100 }}>
    <Spin size="large" />
  </div>
)

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Suspense fallback={PageLoader}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
              <Route index element={<Dashboard />} />
              <Route path="knowledge-bases" element={<KnowledgeBases />} />
              <Route path="upload" element={<DocumentUpload />} />
              <Route path="search" element={<Search />} />
              <Route path="chat" element={<Chat />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="frontier" element={<FrontierDiscovery />} />
              <Route path="literature-reading" element={<LiteratureReading />} />
              <Route path="research-design" element={<ResearchDesign />} />
              <Route path="grant-materials" element={<GrantMaterials />} />
              <Route path="sync-tasks" element={<SyncTasks />} />
              <Route path="preferences" element={<Preferences />} />
              <Route path="paper-analysis" element={<PaperAnalysis />} />
              <Route path="papers" element={<PaperEditor />} />
              <Route path="admin/users" element={<AdminRoute><Users /></AdminRoute>} />
              <Route path="admin/audit-logs" element={<AdminRoute><AuditLogs /></AdminRoute>} />
              <Route path="admin/settings" element={<AdminRoute><SystemSettings /></AdminRoute>} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ErrorBoundary>
  )
}
