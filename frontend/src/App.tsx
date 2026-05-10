import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import AppLayout from '@/components/Layout/AppLayout'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import KnowledgeBases from '@/pages/KnowledgeBases'
import DocumentUpload from '@/pages/DocumentUpload'
import Search from '@/pages/Search'
import Chat from '@/pages/Chat'
import Users from '@/pages/admin/Users'
import AuditLogs from '@/pages/admin/AuditLogs'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.accessToken)
  if (!token) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="knowledge-bases" element={<KnowledgeBases />} />
          <Route path="upload" element={<DocumentUpload />} />
          <Route path="search" element={<Search />} />
          <Route path="chat" element={<Chat />} />
          <Route path="admin/users" element={<Users />} />
          <Route path="admin/audit-logs" element={<AuditLogs />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
