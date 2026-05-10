import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Avatar, Dropdown, theme } from 'antd'
import {
  DashboardOutlined,
  DatabaseOutlined,
  UploadOutlined,
  SearchOutlined,
  MessageOutlined,
  UserOutlined,
  AuditOutlined,
  LogoutOutlined,
  BookOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'

const { Header, Sider, Content } = Layout

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const { token } = theme.useToken()

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: '工作台' },
    { key: '/knowledge-bases', icon: <DatabaseOutlined />, label: '知识库' },
    { key: '/upload', icon: <UploadOutlined />, label: '文档上传' },
    { key: '/search', icon: <SearchOutlined />, label: '智能检索' },
    { key: '/chat', icon: <MessageOutlined />, label: '智能问答' },
    ...(user?.role === 'admin'
      ? [
          { type: 'divider' as const },
          { key: '/admin/users', icon: <UserOutlined />, label: '用户管理' },
          { key: '/admin/audit-logs', icon: <AuditOutlined />, label: '审计日志' },
        ]
      : []),
  ]

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: user?.full_name || '用户' },
    { key: 'logout', icon: <LogoutOutlined />, label: '退出登录' },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}>
        <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <BookOutlined style={{ fontSize: 24, color: '#fff' }} />
          {!collapsed && (
            <span style={{ color: '#fff', fontSize: 18, fontWeight: 'bold', marginLeft: 8 }}>
              MEKS
            </span>
          )}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: token.colorBgContainer,
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
          }}
        >
          <Dropdown
            menu={{
              items: userMenuItems,
              onClick: ({ key }) => {
                if (key === 'logout') {
                  logout()
                  navigate('/login')
                }
              },
            }}
          >
            <Avatar icon={<UserOutlined />} style={{ cursor: 'pointer' }} />
          </Dropdown>
        </Header>
        <Content style={{ margin: 24, padding: 24, background: token.colorBgContainer, borderRadius: 8 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
