import { useState, useEffect } from 'react'
import { Input, Card, List, Tag, Typography, Select, Spin, Empty } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { searchApi, SearchResultItem } from '@/api/search'
import { useKBStore } from '@/stores/knowledgeBaseStore'
import DocumentDetail from '@/components/documents/DocumentDetail'

const { Title, Text, Paragraph } = Typography

export default function Search() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResultItem[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedKbs, setSelectedKbs] = useState<string[]>([])
  const [durationMs, setDurationMs] = useState(0)
  const [viewDocId, setViewDocId] = useState<string | null>(null)

  const { kbs, fetchKbs } = useKBStore()

  useEffect(() => {
    fetchKbs()
  }, [fetchKbs])

  const handleSearch = async (value: string) => {
    if (!value.trim()) return
    setLoading(true)
    try {
      const res = await searchApi.semantic({
        query: value,
        knowledge_base_ids: selectedKbs.length > 0 ? selectedKbs : undefined,
        top_k: 10,
      })
      setResults(res.data.results)
      setDurationMs(res.data.duration_ms)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Title level={4}>智能检索</Title>

      <Card style={{ marginBottom: 16 }}>
        <Select
          mode="multiple"
          style={{ width: '100%', marginBottom: 12 }}
          placeholder="选择知识库范围（不选则搜索全部）"
          onChange={setSelectedKbs}
          options={kbs.map((kb) => ({ value: kb.id, label: kb.name }))}
        />
        <Input.Search
          size="large"
          placeholder="输入您的研究问题，例如：心脏瓣膜病的微创治疗进展"
          enterButton={<><SearchOutlined /> 检索</>}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onSearch={handleSearch}
          loading={loading}
        />
      </Card>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}><Spin size="large" /></div>
      ) : results.length > 0 ? (
        <>
          <Text type="secondary" style={{ marginBottom: 12, display: 'block' }}>
            找到 {results.length} 条相关结果，耗时 {durationMs}ms
          </Text>
          <List
            dataSource={results}
            renderItem={(item) => (
              <Card style={{ marginBottom: 12 }} size="small">
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <a
                    onClick={() => setViewDocId(item.document_id)}
                    style={{ fontWeight: 600, cursor: 'pointer' }}
                  >
                    {item.document_title}
                  </a>
                  <Tag color="blue">相关度 {(item.score * 100).toFixed(1)}%</Tag>
                </div>
                {item.authors && <Text type="secondary">{item.authors}</Text>}
                {item.journal && <Tag style={{ marginLeft: 8 }}>{item.journal}</Tag>}
                <Paragraph
                  style={{ marginTop: 8, background: '#f9f9f9', padding: 12, borderRadius: 4 }}
                  ellipsis={{ rows: 3, expandable: true }}
                >
                  {item.chunk_content}
                </Paragraph>
              </Card>
            )}
          />
        </>
      ) : query ? (
        <Empty description="未找到相关结果" />
      ) : null}

      <DocumentDetail
        documentId={viewDocId}
        open={!!viewDocId}
        onClose={() => setViewDocId(null)}
      />
    </div>
  )
}
