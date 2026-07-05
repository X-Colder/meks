import { useEffect, useState } from 'react'
import { Button, Card, Col, Empty, Row, Select, Space, Spin, Table, Tag, Typography, message } from 'antd'
import { ReadOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import { documentsApi, DocumentItem } from '@/api/documents'
import { knowledgeBasesApi, KnowledgeBase } from '@/api/knowledgeBases'
import { readingCardsApi } from '@/api/readingCards'
import DocumentDetail from '@/components/documents/DocumentDetail'
import '@/styles/chat-markdown.css'

const { Title, Text } = Typography

export default function LiteratureReading() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [kbId, setKbId] = useState<string>()
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [docTotal, setDocTotal] = useState(0)
  const [docPage, setDocPage] = useState(1)
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null)
  const [viewDocId, setViewDocId] = useState<string | null>(null)
  const [loadingDocs, setLoadingDocs] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [loadingCard, setLoadingCard] = useState(false)
  const [readingCard, setReadingCard] = useState('')
  const [cardUpdatedAt, setCardUpdatedAt] = useState<string | null>(null)
  const [cardQueued, setCardQueued] = useState(false)

  useEffect(() => {
    knowledgeBasesApi.list().then((res) => {
      setKbs(res.data)
      if (res.data[0]) setKbId(res.data[0].id)
    })
  }, [])

  useEffect(() => {
    if (!kbId) return
    setLoadingDocs(true)
    documentsApi.list({ knowledge_base_id: kbId, page: docPage, page_size: 10 })
      .then((res) => {
        setDocuments(res.data.items)
        setDocTotal(res.data.total)
      })
      .finally(() => setLoadingDocs(false))
  }, [kbId, docPage])

  useEffect(() => {
    if (!selectedDoc) {
      setReadingCard('')
      setCardUpdatedAt(null)
      setCardQueued(false)
      return
    }
    setLoadingCard(true)
    readingCardsApi.get(selectedDoc.id)
      .then((res) => {
        setReadingCard(res.data.content)
        setCardUpdatedAt(res.data.updated_at)
        setCardQueued(false)
      })
      .catch(() => {
        setReadingCard('')
        setCardUpdatedAt(null)
      })
      .finally(() => setLoadingCard(false))
  }, [selectedDoc])

  const generateCard = async () => {
    if (!selectedDoc) {
      message.warning('请先选择一篇论文')
      return
    }
    setGenerating(true)
    try {
      await readingCardsApi.generate(selectedDoc.id)
      setCardQueued(true)
      message.success('精读卡片生成任务已提交')
    } catch {
      message.error('提交精读卡片生成任务失败')
    } finally {
      setGenerating(false)
    }
  }

  useEffect(() => {
    if (!selectedDoc || !cardQueued) return
    const timer = setInterval(() => {
      readingCardsApi.get(selectedDoc.id)
        .then((res) => {
          setReadingCard(res.data.content)
          setCardUpdatedAt(res.data.updated_at)
          setCardQueued(false)
          clearInterval(timer)
        })
        .catch(() => {})
    }, 3000)
    return () => clearInterval(timer)
  }, [selectedDoc, cardQueued])

  return (
    <div>
      <Title level={4}><ReadOutlined /> 文献精读</Title>
      <Text type="secondary">把论文快速转成医生可读的研究问题、方法、结论和引用建议。</Text>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card size="small" title="选择论文">
            <Space style={{ marginBottom: 12 }}>
              <Select
                style={{ width: 280 }}
                value={kbId}
                onChange={(value) => { setKbId(value); setDocPage(1); setSelectedDoc(null); setReadingCard('') }}
                options={kbs.map((kb) => ({ value: kb.id, label: kb.name }))}
              />
              <Button type="primary" icon={<SafetyCertificateOutlined />} loading={generating} onClick={generateCard}>
                {readingCard ? '重新生成' : '生成精读卡片'}
              </Button>
            </Space>
            <Table
              rowKey="id"
              size="small"
              loading={loadingDocs}
              dataSource={documents}
              rowClassName={(record) => record.id === selectedDoc?.id ? 'ant-table-row-selected' : ''}
              onRow={(record) => ({ onClick: () => setSelectedDoc(record), style: { cursor: 'pointer' } })}
              columns={[
                { title: '标题', dataIndex: 'title', ellipsis: true, render: (title: string, record) => <a onClick={(e) => { e.stopPropagation(); setViewDocId(record.id) }}>{title}</a> },
                { title: '状态', dataIndex: 'status', width: 90, render: (status: string) => <Tag color={status === 'indexed' ? 'success' : 'default'}>{status}</Tag> },
                { title: '日期', dataIndex: 'publication_date', width: 110, render: (value: string | null) => value || '-' },
              ]}
              pagination={{ current: docPage, total: docTotal, pageSize: 10, showSizeChanger: false, onChange: setDocPage }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card size="small" title={selectedDoc ? `精读卡片：${selectedDoc.title}` : '精读卡片'}>
            {cardUpdatedAt && <Text type="secondary">已保存：{cardUpdatedAt.slice(0, 19).replace('T', ' ')}</Text>}
            <Spin spinning={generating || loadingCard}>
              {readingCard ? (
                <div className="chat-markdown"><ReactMarkdown>{readingCard}</ReactMarkdown></div>
              ) : cardQueued ? (
                <Empty description="精读卡片正在后台生成，请稍候..." />
              ) : (
                <Empty description="选择论文后生成精读卡片" />
              )}
            </Spin>
          </Card>
        </Col>
      </Row>
      <DocumentDetail documentId={viewDocId} open={!!viewDocId} onClose={() => setViewDocId(null)} />
    </div>
  )
}
