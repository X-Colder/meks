import { useEffect, useState, useCallback } from 'react'
import { Table, Select, Input, DatePicker, Tag, Typography, Space } from 'antd'
import { auditLogsApi, AuditLog } from '@/api/auditLogs'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'

const { Title } = Typography
const { RangePicker } = DatePicker

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [actionFilter, setActionFilter] = useState<string | undefined>()
  const [userIdFilter, setUserIdFilter] = useState<string | undefined>()
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)

  const fetchLogs = useCallback(async (p: number) => {
    setLoading(true)
    try {
      const res = await auditLogsApi.list({
        page: p,
        page_size: 10,
        action: actionFilter,
        user_id: userIdFilter || undefined,
        start_date: dateRange?.[0]?.toISOString(),
        end_date: dateRange?.[1]?.toISOString(),
      })
      setLogs(res.data.items)
      setTotal(res.data.total)
    } finally {
      setLoading(false)
    }
  }, [actionFilter, userIdFilter, dateRange])

  useEffect(() => {
    fetchLogs(page)
  }, [page, fetchLogs])

  const columns: ColumnsType<AuditLog> = [
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => <Tag color="blue">{action}</Tag>,
    },
    { title: '资源类型', dataIndex: 'resource_type', key: 'resource_type' },
    { title: '资源ID', dataIndex: 'resource_id', key: 'resource_id' },
    {
      title: '详情',
      dataIndex: 'details',
      key: 'details',
      ellipsis: true,
      width: 300,
    },
    { title: 'IP地址', dataIndex: 'ip_address', key: 'ip_address' },
  ]

  return (
    <div>
      <Title level={4}>审计日志</Title>

      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          allowClear
          style={{ width: 160 }}
          placeholder="操作类型"
          value={actionFilter}
          onChange={(val) => {
            setActionFilter(val)
            setPage(1)
          }}
          options={[
            { value: 'login', label: '登录' },
            { value: 'logout', label: '登出' },
            { value: 'create', label: '创建' },
            { value: 'update', label: '更新' },
            { value: 'delete', label: '删除' },
            { value: 'search', label: '检索' },
            { value: 'upload', label: '上传' },
          ]}
        />
        <Input
          allowClear
          style={{ width: 200 }}
          placeholder="用户ID"
          value={userIdFilter}
          onChange={(e) => {
            setUserIdFilter(e.target.value || undefined)
            setPage(1)
          }}
        />
        <RangePicker
          onChange={(dates) => {
            setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)
            setPage(1)
          }}
        />
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={logs}
        loading={loading}
        expandable={{
          expandedRowRender: (record) => <p style={{ margin: 0 }}>{record.details}</p>,
          rowExpandable: (record) => !!record.details,
        }}
        pagination={{
          current: page,
          total,
          pageSize: 10,
          onChange: setPage,
        }}
      />
    </div>
  )
}
