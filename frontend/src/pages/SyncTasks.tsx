import { useEffect, useState, useCallback, useRef } from 'react'
import {
  Table, Button, Modal, Form, Input, Select, Badge, Tag, Typography, Space, message, Drawer, List,
} from 'antd'
import { PlusOutlined, PlayCircleOutlined, PauseCircleOutlined, DeleteOutlined, FileTextOutlined, ReloadOutlined } from '@ant-design/icons'
import { syncTasksApi, SyncTask } from '@/api/syncTasks'
import { knowledgeBasesApi, KnowledgeBase } from '@/api/knowledgeBases'
import { documentsApi, DocumentItem } from '@/api/documents'
import type { ColumnsType } from 'antd/es/table'
import DocumentDetail from '@/components/documents/DocumentDetail'

const { Title, Text } = Typography

const statusMap: Record<string, { status: 'default' | 'processing' | 'warning' | 'error'; text: string }> = {
  idle: { status: 'default', text: '空闲' },
  running: { status: 'processing', text: '运行中' },
  paused: { status: 'warning', text: '已暂停' },
  failed: { status: 'error', text: '失败' },
}

export default function SyncTasks() {
  const [tasks, setTasks] = useState<SyncTask[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [form] = Form.useForm()

  const [detailTask, setDetailTask] = useState<SyncTask | null>(null)
  const [detailDocs, setDetailDocs] = useState<DocumentItem[]>([])
  const [detailTotal, setDetailTotal] = useState(0)
  const [detailPage, setDetailPage] = useState(1)
  const [detailLoading, setDetailLoading] = useState(false)
  const [viewDocId, setViewDocId] = useState<string | null>(null)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchTasks = useCallback(async (p: number) => {
    setLoading(true)
    try {
      const res = await syncTasksApi.list({ page: p, page_size: 10 })
      setTasks(res.data.items)
      setTotal(res.data.total)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTasks(page)
    knowledgeBasesApi.list().then((res) => setKbs(res.data))
  }, [page, fetchTasks])

  useEffect(() => {
    const hasRunning = tasks.some((t) => t.status === 'running')
    if (hasRunning && !pollRef.current) {
      pollRef.current = setInterval(() => fetchTasks(page), 5000)
    } else if (!hasRunning && pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    return () => {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    }
  }, [tasks, page, fetchTasks])

  const handleCreate = async (values: { name: string; source_type: string; query: string; max_results?: number; cron_expr?: string; target_kb_id: string }) => {
    await syncTasksApi.create({
      name: values.name,
      source_type: values.source_type,
      config: { query: values.query, max_results: values.max_results || 20 },
      cron_expr: values.cron_expr,
      target_kb_id: values.target_kb_id,
    })
    message.success('同步任务创建成功')
    setModalOpen(false)
    form.resetFields()
    fetchTasks(page)
  }

  const handleRun = async (id: string) => {
    await syncTasksApi.run(id)
    message.success('任务已启动')
    fetchTasks(page)
  }

  const handlePause = async (id: string) => {
    await syncTasksApi.pause(id)
    message.success('任务已暂停')
    fetchTasks(page)
  }

  const handleDelete = (task: SyncTask) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除同步任务 "${task.name}" 吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        await syncTasksApi.delete(task.id)
        message.success('任务已删除')
        fetchTasks(page)
      },
    })
  }

  const handleViewDocs = async (task: SyncTask) => {
    setDetailTask(task)
    setDetailPage(1)
    setDetailLoading(true)
    try {
      const res = await documentsApi.list({ knowledge_base_id: task.target_kb_id, page: 1, page_size: 10 })
      setDetailDocs(res.data.items)
      setDetailTotal(res.data.total)
    } finally {
      setDetailLoading(false)
    }
  }

  const refreshDetailDocs = async (p = detailPage) => {
    if (!detailTask) return
    setDetailLoading(true)
    try {
      const res = await documentsApi.list({ knowledge_base_id: detailTask.target_kb_id, page: p, page_size: 10 })
      setDetailDocs(res.data.items)
      setDetailTotal(res.data.total)
    } finally {
      setDetailLoading(false)
    }
  }

  useEffect(() => {
    if (detailTask) refreshDetailDocs(detailPage)
  }, [detailPage])

  const handleReindexDoc = async (doc: DocumentItem) => {
    await documentsApi.reindex(doc.id)
    message.success('已提交重新索引')
    refreshDetailDocs()
  }

  const handleReindexTaskDocs = async () => {
    if (!detailTask) return
    const res = await documentsApi.reindexBatch({ knowledge_base_id: detailTask.target_kb_id, limit: 100 })
    message.success(res.data.detail || '已提交未索引论文重试')
    refreshDetailDocs()
  }

  const columns: ColumnsType<SyncTask> = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    {
      title: '数据源',
      dataIndex: 'source_type',
      key: 'source_type',
      render: (val: string) => <Tag>{val.toUpperCase()}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const info = statusMap[status] || { status: 'default' as const, text: status }
        return <Badge status={info.status} text={info.text} />
      },
    },
    {
      title: '进度',
      key: 'progress',
      render: (_: unknown, record: SyncTask) => (
        <Text>{record.processed_count} / {record.total_count}</Text>
      ),
    },
    { title: '上次同步', dataIndex: 'last_sync_at', key: 'last_sync_at' },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: SyncTask) => {
        const isRunning = record.status === 'running'
        return (
          <Space>
            <Button type="link" icon={<PlayCircleOutlined />} disabled={isRunning} onClick={() => handleRun(record.id)}>
              运行
            </Button>
            <Button type="link" icon={<PauseCircleOutlined />} disabled={!isRunning} onClick={() => handlePause(record.id)}>
              暂停
            </Button>
            <Button type="link" icon={<FileTextOutlined />} onClick={() => handleViewDocs(record)}>
              查看论文
            </Button>
            <Button type="link" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record)}>
              删除
            </Button>
          </Space>
        )
      },
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4}>同步任务</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新建任务
        </Button>
      </div>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={tasks}
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 10,
          onChange: setPage,
        }}
      />

      <Modal
        title="新建同步任务"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="任务名称" rules={[{ required: true }]}>
            <Input placeholder="例如: PubMed心血管同步" />
          </Form.Item>
          <Form.Item name="source_type" label="数据源类型" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'pmc', label: 'PMC' },
                { value: 'arxiv', label: 'arXiv' },
                { value: 'biorxiv', label: 'bioRxiv/medRxiv' },
                { value: 'europepmc', label: 'Europe PMC' },
                { value: 'semantic_scholar', label: 'Semantic Scholar' },
              ]}
            />
          </Form.Item>
          <Form.Item name="query" label="检索关键词" rules={[{ required: true }]}>
            <Input placeholder="例如: cardiovascular disease" />
          </Form.Item>
          <Form.Item name="max_results" label="下载论文数量" initialValue={20}>
            <Select
              options={[
                { value: 5, label: '5 篇' },
                { value: 10, label: '10 篇' },
                { value: 20, label: '20 篇（默认）' },
                { value: 50, label: '50 篇' },
                { value: 100, label: '100 篇' },
              ]}
            />
          </Form.Item>
          <Form.Item name="cron_expr" label="定时表达式（可选）">
            <Input placeholder="例如: 0 2 * * *（每天凌晨2点）" />
          </Form.Item>
          <Form.Item name="target_kb_id" label="目标知识库" rules={[{ required: true }]}>
            <Select
              placeholder="选择目标知识库"
              options={kbs.map((kb) => ({ value: kb.id, label: kb.name }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Drawer
        title={detailTask ? `已导入论文 — ${detailTask.name}` : '已导入论文'}
        open={!!detailTask}
        onClose={() => setDetailTask(null)}
        width={600}
        extra={
          <Button icon={<ReloadOutlined />} onClick={handleReindexTaskDocs}>
            重试未索引
          </Button>
        }
      >
        <List
          loading={detailLoading}
          dataSource={detailDocs}
          pagination={{
            current: detailPage,
            total: detailTotal,
            pageSize: 10,
            showSizeChanger: false,
            onChange: setDetailPage,
          }}
          renderItem={(doc) => (
            <List.Item>
              <List.Item.Meta
                title={<a onClick={() => setViewDocId(doc.id)} style={{ cursor: 'pointer' }}>{doc.title}</a>}
                description={
                  <Space>
                    <Tag color={doc.status === 'indexed' ? 'success' : doc.status === 'failed' ? 'error' : 'default'}>{doc.status}</Tag>
                    <Text type="secondary">{doc.file_type.toUpperCase()}</Text>
                    <Text type="secondary">{doc.created_at?.slice(0, 10)}</Text>
                  </Space>
                }
              />
              {doc.status !== 'indexed' && (
                <Button size="small" icon={<ReloadOutlined />} onClick={() => handleReindexDoc(doc)}>
                  重试索引
                </Button>
              )}
            </List.Item>
          )}
        />
      </Drawer>

      <DocumentDetail documentId={viewDocId} open={!!viewDocId} onClose={() => setViewDocId(null)} />
    </div>
  )
}
