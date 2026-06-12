import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Avatar, Dropdown, theme } from 'antd'
import {
  DashboardOutlined,
  DatabaseOutlined,
  UploadOutlined,
  UserOutlined,
  AuditOutlined,
  LogoutOutlined,
  BookOutlined,
  BarChartOutlined,
  SyncOutlined,
  SettingOutlined,
  SafetyCertificateOutlined,
  EditOutlined,
  BulbOutlined,
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
    { key: '/analytics', icon: <BarChartOutlined />, label: '统计分析' },
    { key: '/frontier', icon: <BulbOutlined />, label: '前沿发现' },
    { key: '/sync-tasks', icon: <SyncOutlined />, label: '同步任务' },
    { key: '/paper-analysis', icon: <SafetyCertificateOutlined />, label: '论文鉴真' },
    { key: '/papers', icon: <EditOutlined />, label: '论文协作' },
    ...(user?.role === 'admin'
      ? [
          { type: 'divider' as const },
          { key: '/admin/users', icon: <UserOutlined />, label: '用户管理' },
          { key: '/admin/audit-logs', icon: <AuditOutlined />, label: '审计日志' },
          { key: '/admin/settings', icon: <SettingOutlined />, label: '系统设置' },
        ]
      : []),
  ]

  const userMenuItems = [
    { key: 'profile', icon: <UserOutlined />, label: user?.full_name || '用户' },
    { key: 'preferences', icon: <SettingOutlined />, label: '个人偏好' },
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
                } else if (key === 'preferences') {
                  navigate('/preferences')
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
