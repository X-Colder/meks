import { useState, useEffect } from 'react'
import { Input, Button, Table, Select, Tag, Typography, Card, Spin } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { analyticsApi, AnalyticsResponse } from '@/api/analytics'
import { knowledgeBasesApi, KnowledgeBase } from '@/api/knowledgeBases'

const { Title, Text } = Typography

export default function Analytics() {
  const [query, setQuery] = useState('')
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [selectedKbs, setSelectedKbs] = useState<string[]>([])
  const [result, setResult] = useState<AnalyticsResponse | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    knowledgeBasesApi.list().then((res) => setKbs(res.data))
  }, [])

  const handleSubmit = async () => {
    if (!query.trim()) return
    setLoading(true)
    try {
      const res = await analyticsApi.query({
        query,
        knowledge_base_ids: selectedKbs.length > 0 ? selectedKbs : undefined,
      })
      setResult(res.data)
    } finally {
      setLoading(false)
    }
  }

  const dynamicColumns = result
    ? result.columns.map((col) => ({
        title: col,
        dataIndex: col,
        key: col,
      }))
    : []

  return (
    <div>
      <Title level={4}>统计分析</Title>

      <Card style={{ marginBottom: 16 }}>
        <Select
          mode="multiple"
          style={{ width: '100%', marginBottom: 12 }}
          placeholder="选择知识库范围（可选）"
          onChange={setSelectedKbs}
          options={kbs.map((kb) => ({ value: kb.id, label: kb.name }))}
        />
        <Input.TextArea
          rows={3}
          placeholder="输入自然语言查询，例如：各知识库文档数量统计"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ marginBottom: 12 }}
        />
        <Button type="primary" icon={<SearchOutlined />} onClick={handleSubmit} loading={loading}>
          查询
        </Button>
      </Card>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
        </div>
      ) : result ? (
        <>
          <div style={{ marginBottom: 12, display: 'flex', gap: 16, alignItems: 'center' }}>
            <Text>
              意图类型: <Tag color="blue">{result.intent_type}</Tag>
            </Text>
            <Text type="secondary">耗时 {result.duration_ms}ms</Text>
            <Text type="secondary">共 {result.total} 条</Text>
          </div>
          <Table
            rowKey={(_record, index) => String(index)}
            columns={dynamicColumns}
            dataSource={result.rows}
            pagination={{ pageSize: 20 }}
          />
        </>
      ) : null}
    </div>
  )
}
