import { useEffect, useState, useCallback } from 'react'
import {
  Table, Button, Modal, Form, Input, Select, Tag, Badge, Typography, Space, message, Switch,
} from 'antd'
import { PlusOutlined, EditOutlined, KeyOutlined, DeleteOutlined } from '@ant-design/icons'
import { usersApi, User, CreateUserParams, UpdateUserParams } from '@/api/users'
import type { ColumnsType } from 'antd/es/table'

const { Title } = Typography

const roleColors: Record<string, string> = {
  admin: 'red',
  researcher: 'blue',
  doctor: 'green',
  viewer: 'default',
}

export default function Users() {
  const [users, setUsers] = useState<User[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [currentUser, setCurrentUser] = useState<User | null>(null)
  const [createForm] = Form.useForm()
  const [editForm] = Form.useForm()
  const [passwordForm] = Form.useForm()

  const fetchUsers = useCallback(async (p: number) => {
    setLoading(true)
    try {
      const res = await usersApi.list({ page: p, page_size: 10 })
      setUsers(res.data.items)
      setTotal(res.data.total)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUsers(page)
  }, [page, fetchUsers])

  const handleCreate = async (values: CreateUserParams) => {
    await usersApi.create(values)
    message.success('用户创建成功')
    setCreateOpen(false)
    createForm.resetFields()
    fetchUsers(page)
  }

  const handleEdit = async (values: UpdateUserParams) => {
    if (!currentUser) return
    await usersApi.update(currentUser.id, values)
    message.success('用户更新成功')
    setEditOpen(false)
    editForm.resetFields()
    setCurrentUser(null)
    fetchUsers(page)
  }

  const handleResetPassword = async (values: { new_password: string }) => {
    if (!currentUser) return
    await usersApi.resetPassword(currentUser.id, values.new_password)
    message.success('密码重置成功')
    setPasswordOpen(false)
    passwordForm.resetFields()
    setCurrentUser(null)
  }

  const handleDelete = (user: User) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除用户 "${user.username}" 吗？此操作不可撤销。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        await usersApi.delete(user.id)
        message.success('用户已删除')
        fetchUsers(page)
      },
    })
  }

  const openEdit = (user: User) => {
    setCurrentUser(user)
    editForm.setFieldsValue({
      email: user.email,
      full_name: user.full_name,
      role: user.role,
      department: user.department,
      is_active: user.is_active,
    })
    setEditOpen(true)
  }

  const openResetPassword = (user: User) => {
    setCurrentUser(user)
    setPasswordOpen(true)
  }

  const columns: ColumnsType<User> = [
    { title: '用户名', dataIndex: 'username', key: 'username' },
    { title: '姓名', dataIndex: 'full_name', key: 'full_name' },
    { title: '邮箱', dataIndex: 'email', key: 'email' },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => <Tag color={roleColors[role] || 'default'}>{role}</Tag>,
    },
    { title: '科室', dataIndex: 'department', key: 'department' },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Badge status={active ? 'success' : 'error'} text={active ? '启用' : '禁用'} />
      ),
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: User) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Button type="link" icon={<KeyOutlined />} onClick={() => openResetPassword(record)}>
            重置密码
          </Button>
          <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record)}>
            删除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4}>用户管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          新建用户
        </Button>
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={users}
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 10,
          onChange: setPage,
        }}
      />

      {/* Create User Modal */}
      <Modal
        title="新建用户"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => createForm.submit()}
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="full_name" label="姓名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'admin', label: '管理员' },
                { value: 'researcher', label: '研究员' },
                { value: 'doctor', label: '医生' },
                { value: 'viewer', label: '访客' },
              ]}
            />
          </Form.Item>
          <Form.Item name="department" label="科室">
            <Input />
          </Form.Item>
        </Form>
      </Modal>

      {/* Edit User Modal */}
      <Modal
        title="编辑用户"
        open={editOpen}
        onCancel={() => {
          setEditOpen(false)
          setCurrentUser(null)
          editForm.resetFields()
        }}
        onOk={() => editForm.submit()}
      >
        <Form form={editForm} layout="vertical" onFinish={handleEdit}>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="full_name" label="姓名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'admin', label: '管理员' },
                { value: 'researcher', label: '研究员' },
                { value: 'doctor', label: '医生' },
                { value: 'viewer', label: '访客' },
              ]}
            />
          </Form.Item>
          <Form.Item name="department" label="科室">
            <Input />
          </Form.Item>
          <Form.Item name="is_active" label="启用状态" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      {/* Reset Password Modal */}
      <Modal
        title="重置密码"
        open={passwordOpen}
        onCancel={() => {
          setPasswordOpen(false)
          setCurrentUser(null)
          passwordForm.resetFields()
        }}
        onOk={() => passwordForm.submit()}
      >
        <Form form={passwordForm} layout="vertical" onFinish={handleResetPassword}>
          <Form.Item name="new_password" label="新密码" rules={[{ required: true, min: 6 }]}>
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
