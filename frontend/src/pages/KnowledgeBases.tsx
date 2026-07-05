import { useEffect, useState, useRef, useCallback } from 'react'
import { Card, Button, Modal, Form, Input, Select, List, Tag, Typography, message, Radio, Checkbox, Table, Tabs, Spin, Space } from 'antd'
import { PlusOutlined, DatabaseOutlined, ArrowLeftOutlined, SearchOutlined, MessageOutlined, ReloadOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import '@/styles/chat-markdown.css'
import { knowledgeBasesApi, KnowledgeBase } from '@/api/knowledgeBases'
import { documentsApi, DocumentItem } from '@/api/documents'
import { searchApi, SearchResultItem } from '@/api/search'
import DocumentDetail from '@/components/documents/DocumentDetail'
import PaperAnalysisDrawer from '@/components/papers/PaperAnalysisDrawer'
import { PaperAnalysisResult } from '@/api/paperAnalysis'
import type { ColumnsType } from 'antd/es/table'

const medicalRecordCategories = ['患者信息', '就诊信息', '诊断信息', '治疗信息', '转归信息', '病史']

const { Title, Text, Paragraph } = Typography

const visibilityColor: Record<string, string> = { public: 'green', department: 'blue', private: 'default' }

function KBDetail({ kb, onBack }: { kb: KnowledgeBase; onBack: () => void }) {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [docsLoading, setDocsLoading] = useState(false)
  const [docsTotal, setDocsTotal] = useState(0)
  const [docsPage, setDocsPage] = useState(1)
  const [viewDocId, setViewDocId] = useState<string | null>(null)
  const [analysisDoc, setAnalysisDoc] = useState<DocumentItem | null>(null)
  const [analysisOpen, setAnalysisOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [chatMessages, setChatMessages] = useState<{ role: string; content: string; done?: boolean }[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [relatedDocIds, setRelatedDocIds] = useState<Set<string>>(new Set())
  const [leftWidth, setLeftWidth] = useState(55)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const fetchDocuments = useCallback(() => {
    setDocsLoading(true)
    documentsApi.list({ knowledge_base_id: kb.id, page: docsPage, page_size: 10 })
      .then((res) => {
        setDocuments(res.data.items)
        setDocsTotal(res.data.total)
      })
      .finally(() => setDocsLoading(false))
  }, [kb.id, docsPage])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  useEffect(() => {
    setDocsPage(1)
  }, [kb.id])

  const [chatHeight, setChatHeight] = useState(400)
  const resizingChat = useRef(false)
  const chatContainerRef = useRef<HTMLDivElement>(null)
  const userScrolledUp = useRef(false)

  useEffect(() => {
    if (!userScrolledUp.current) {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [chatMessages])

  const handleChatScroll = () => {
    const el = chatContainerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50
    userScrolledUp.current = !atBottom
  }

  const onChatResizeStart = () => { resizingChat.current = true }
  const onChatResizeEnd = () => { resizingChat.current = false }
  const onChatResizeMove = (e: React.MouseEvent) => {
    if (!resizingChat.current) return
    const container = e.currentTarget.getBoundingClientRect()
    const newH = e.clientY - container.top
    if (newH > 150 && newH < 800) setChatHeight(newH)
  }

  const handleMouseDown = () => { dragging.current = true }
  const handleMouseUp = () => { dragging.current = false }
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragging.current || !containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    const pct = ((e.clientX - rect.left) / rect.width) * 100
    if (pct > 25 && pct < 75) setLeftWidth(pct)
  }

  const handleSearch = async (value: string) => {
    if (!value.trim()) { setSearchResults([]); setRelatedDocIds(new Set()); return }
    setSearchLoading(true)
    try {
      const res = await searchApi.semantic({ query: value, knowledge_base_ids: [kb.id], top_k: 10 })
      setSearchResults(res.data.results)
      setRelatedDocIds(new Set(res.data.results.map(r => r.document_id)))
    } finally { setSearchLoading(false) }
  }

  const getToken = () => {
    try { return JSON.parse(localStorage.getItem('meks-auth') || '{}').state?.accessToken || '' }
    catch { return '' }
  }

  const handleChat = async () => {
    if (!chatInput.trim() || chatLoading) return
    const userMsg = chatInput.trim()
    setChatInput('')
    setChatMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setChatMessages(prev => [...prev, { role: 'assistant', content: '' }])
    setChatLoading(true)

    try {
      const token = getToken()
      const sessionRes = await fetch('/api/v1/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ knowledge_base_ids: [kb.id] }),
      })
      const session = await sessionRes.json()

      const msgRes = await fetch(`/api/v1/chat/sessions/${session.id}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ content: userMsg }),
      })

      let fullResponse = ''
      const reader = msgRes.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            const cleaned = line.replace(/\r/g, '')
            if (cleaned.startsWith('event: done')) break
            if (cleaned.startsWith('data:')) {
              const payload = cleaned.substring(5)
              if (payload.trim() === '') {
                fullResponse += '\n'
              } else if (payload.startsWith(' ')) {
                fullResponse += payload.substring(1)
              } else {
                fullResponse += payload
              }
            }
          }

          setChatMessages(prev => {
            const updated = [...prev]
            updated[updated.length - 1] = { role: 'assistant', content: fullResponse }
            return updated
          })
        }
      }

      if (!fullResponse) {
        setChatMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: '暂无回答', done: true }
          return updated
        })
      } else {
        const cleaned = fullResponse
          .replace(/\*\* /g, '**')
          .replace(/ \*\*/g, '**')
          .replace(/\* /g, '*')
          .replace(/ \*/g, '*')
          .replace(/\*\*([^*]+)\*\*/g, (_, m) => `**${m.trim()}**`)
        setChatMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: cleaned, done: true }
          return updated
        })
      }

      userScrolledUp.current = false

      const searchRes = await searchApi.semantic({ query: userMsg, knowledge_base_ids: [kb.id], top_k: 5 })
      setRelatedDocIds(new Set(searchRes.data.results.map(r => r.document_id)))
    } catch {
      setChatMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: 'assistant', content: '请求失败，请重试' }
        return updated
      })
    } finally { setChatLoading(false) }
  }

  const filteredDocs = relatedDocIds.size > 0 ? documents.filter(d => relatedDocIds.has(d.id)) : documents

  const handleReindexDoc = async (doc: DocumentItem) => {
    await documentsApi.reindex(doc.id)
    message.success('已提交重新索引')
    fetchDocuments()
  }

  const handleReindexUnindexed = async () => {
    const res = await documentsApi.reindexBatch({ knowledge_base_id: kb.id, limit: 100 })
    message.success(res.data.detail || '已提交未索引论文重试')
    fetchDocuments()
  }

  const handleOpenAnalysis = (doc: DocumentItem) => {
    setAnalysisDoc(doc)
    setAnalysisOpen(true)
  }

  const handleAnalysisUpdated = (documentId: string, result: PaperAnalysisResult) => {
    setDocuments((prev) => prev.map((doc) => (
      doc.id === documentId
        ? {
            ...doc,
            analysis_status: result.status,
            analysis_risk_score: result.overall_risk_score,
            risk_level: result.risk_level,
          }
        : doc
    )))
  }

  const docColumns: ColumnsType<DocumentItem> = [
    { title: '论文标题', dataIndex: 'title', ellipsis: true, render: (title: string, record) => <a onClick={() => setViewDocId(record.id)} style={{ cursor: 'pointer' }}>{title}</a> },
    { title: '类型', dataIndex: 'file_type', width: 60, render: (v: string) => <Tag>{v.toUpperCase()}</Tag> },
    { title: '状态', dataIndex: 'status', width: 80, render: (v: string) => <Tag color={v === 'indexed' ? 'success' : v === 'failed' ? 'error' : 'default'}>{v}</Tag> },
    {
      title: '鉴真',
      key: 'analysis',
      width: 120,
      render: (_: unknown, record) => {
        const done = record.analysis_status === 'completed'
        const running = record.analysis_status === 'pending' || record.analysis_status === 'analyzing'
        return (
          <Button
            size="small"
            icon={<SafetyCertificateOutlined style={{ color: done ? '#52c41a' : undefined }} />}
            disabled={record.status !== 'indexed'}
            onClick={() => handleOpenAnalysis(record)}
            style={done ? { color: '#389e0d', borderColor: '#52c41a' } : undefined}
          >
            {done ? '鉴真完成' : running ? '生成中' : '论文鉴真'}
          </Button>
        )
      },
    },
    { title: '作者', dataIndex: 'authors', ellipsis: true, width: 180 },
    {
      title: '操作',
      key: 'actions',
      width: 100,
      render: (_: unknown, record) => (
        <Space size={4}>
          {record.status !== 'indexed' && (
            <Button size="small" icon={<ReloadOutlined />} onClick={() => handleReindexDoc(record)}>重试</Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={onBack} style={{ marginRight: 12 }} />
        <Title level={4} style={{ margin: 0 }}>{kb.name}</Title>
        <Tag style={{ marginLeft: 12 }}>{documents.length} 篇文档</Tag>
      </div>

      <div ref={containerRef} style={{ display: 'flex', height: 'calc(100vh - 180px)' }} onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
        <div style={{ width: `${leftWidth}%`, overflow: 'auto' }}>
          <Tabs items={[
            {
              key: 'search', label: <span><SearchOutlined /> 智能检索</span>,
              children: (
                <div>
                  <Input.Search placeholder="输入关键词检索该知识库中的论文..." enterButton="检索" loading={searchLoading} value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} onSearch={handleSearch} style={{ marginBottom: 12 }} />
                  {searchResults.length > 0 && (
                    <List size="small" dataSource={searchResults} renderItem={(item) => (
                      <List.Item>
                        <List.Item.Meta
                          title={<a onClick={() => setViewDocId(item.document_id)} style={{ cursor: 'pointer' }}>{item.document_title}</a>}
                          description={<Paragraph ellipsis={{ rows: 2 }} style={{ margin: 0, fontSize: 12 }}>{item.chunk_content}</Paragraph>}
                        />
                        <Tag color="blue">{(item.score * 100).toFixed(0)}%</Tag>
                      </List.Item>
                    )} />
                  )}
                </div>
              ),
            },
            {
              key: 'chat', label: <span><MessageOutlined /> 智能问答</span>,
              children: (
                <div onMouseMove={onChatResizeMove} onMouseUp={onChatResizeEnd} onMouseLeave={onChatResizeEnd}>
                  <div ref={chatContainerRef} onScroll={handleChatScroll} style={{ height: chatHeight, overflowY: 'auto', border: '1px solid #f0f0f0', borderRadius: 8, padding: 16, background: '#fafafa' }}>
                    {chatMessages.length === 0 && <Text type="secondary">基于该知识库提问，AI 将引用相关论文回答</Text>}
                    {chatMessages.map((msg, i) => (
                      <div key={i} style={{ marginBottom: 16, textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                        <div style={{ display: 'inline-block', maxWidth: '90%', padding: msg.role === 'user' ? '8px 14px' : '12px 16px', borderRadius: 8, background: msg.role === 'user' ? '#1677ff' : '#fff', color: msg.role === 'user' ? '#fff' : '#333', border: msg.role === 'user' ? 'none' : '1px solid #e8e8e8', textAlign: 'left' }}>
                          {msg.role === 'user' ? (
                            <span style={{ color: '#fff' }}>{msg.content}</span>
                          ) : msg.done ? (
                            <div className="chat-markdown" style={{ lineHeight: 1.8, fontSize: 14 }}>
                              <ReactMarkdown>{msg.content}</ReactMarkdown>
                            </div>
                          ) : (
                            <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'inherit', fontSize: 14, lineHeight: 1.8 }}>{msg.content || '...'}</pre>
                          )}
                        </div>
                      </div>
                    ))}
                    {chatLoading && <div><Spin size="small" /> <Text type="secondary">AI 正在分析中...</Text></div>}
                    <div ref={chatEndRef} />
                  </div>
                  <div onMouseDown={onChatResizeStart} style={{ height: 6, cursor: 'ns-resize', background: '#f0f0f0', borderRadius: 3, margin: '4px 0', transition: 'background 0.2s' }} onMouseEnter={(e) => (e.currentTarget.style.background = '#1677ff')} onMouseLeave={(e) => (e.currentTarget.style.background = '#f0f0f0')} />
                  <Input.Search placeholder="输入问题..." enterButton="发送" value={chatInput} onChange={(e) => setChatInput(e.target.value)} onSearch={handleChat} loading={chatLoading} />
                </div>
              ),
            },
          ]} />
        </div>

        <div onMouseDown={handleMouseDown} style={{ width: 6, cursor: 'col-resize', background: '#f0f0f0', flexShrink: 0, borderRadius: 3, transition: 'background 0.2s' }} onMouseEnter={(e) => (e.currentTarget.style.background = '#1677ff')} onMouseLeave={(e) => (e.currentTarget.style.background = '#f0f0f0')} />

        <div style={{ width: `${100 - leftWidth}%`, overflow: 'auto', paddingLeft: 12 }}>
          <Card
            title={relatedDocIds.size > 0 ? `相关论文 (${filteredDocs.length})` : `全部论文 (${documents.length})`}
            size="small"
            extra={<Button size="small" icon={<ReloadOutlined />} onClick={handleReindexUnindexed}>重试未索引</Button>}
          >
            {relatedDocIds.size > 0 && <Button type="link" size="small" onClick={() => setRelatedDocIds(new Set())} style={{ marginBottom: 8, padding: 0 }}>显示全部</Button>}
            <Table
              rowKey="id"
              columns={docColumns}
              dataSource={filteredDocs}
              loading={docsLoading}
              size="small"
              pagination={relatedDocIds.size > 0 ? { pageSize: 10, showSizeChanger: false } : {
                current: docsPage,
                total: docsTotal,
                pageSize: 10,
                showSizeChanger: false,
                onChange: setDocsPage,
              }}
            />
          </Card>
        </div>
      </div>

      <DocumentDetail documentId={viewDocId} open={!!viewDocId} onClose={() => setViewDocId(null)} />
      <PaperAnalysisDrawer
        open={analysisOpen}
        documentId={analysisDoc?.id || null}
        title={analysisDoc?.title || ''}
        initialStatus={analysisDoc?.analysis_status}
        onClose={() => setAnalysisOpen(false)}
        onStatusChange={handleAnalysisUpdated}
      />
    </div>
  )
}

export default function KnowledgeBases() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()
  const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null)
  const [kbType, setKbType] = useState<string>('literature')

  const fetchKbs = async () => {
    setLoading(true)
    try { const res = await knowledgeBasesApi.list(); setKbs(res.data) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchKbs() }, [])

  const handleCreate = async (values: Record<string, unknown>) => {
    await knowledgeBasesApi.create(values as Parameters<typeof knowledgeBasesApi.create>[0])
    message.success('知识库创建成功')
    setModalOpen(false)
    form.resetFields()
    setKbType('literature')
    fetchKbs()
  }

  if (selectedKb) {
    return <KBDetail kb={selectedKb} onBack={() => setSelectedKb(null)} />
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4}>知识库管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>新建知识库</Button>
      </div>

      <List loading={loading} grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 3 }} dataSource={kbs} renderItem={(kb) => (
        <List.Item>
          <Card hoverable onClick={() => setSelectedKb(kb)} style={{ cursor: 'pointer' }}>
            <Card.Meta
              avatar={<DatabaseOutlined style={{ fontSize: 32, color: '#1677ff' }} />}
              title={kb.name}
              description={<><Text type="secondary">{kb.description || '暂无描述'}</Text><div style={{ marginTop: 8 }}><Tag color={visibilityColor[kb.visibility]}>{kb.visibility}</Tag><Tag>{kb.document_count} 篇文档</Tag></div></>}
            />
          </Card>
        </List.Item>
      )} />

      <Modal title="新建知识库" open={modalOpen} onCancel={() => setModalOpen(false)} onOk={() => form.submit()}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}><Input placeholder="例如: 心血管前沿研究" /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea placeholder="知识库用途描述" /></Form.Item>
          <Form.Item name="visibility" label="可见范围" initialValue="department">
            <Select options={[{ value: 'public', label: '全院公开' }, { value: 'department', label: '科室可见' }, { value: 'private', label: '仅自己' }]} />
          </Form.Item>
          <Form.Item name="kb_type" label="知识库类型" initialValue="literature">
            <Radio.Group onChange={(e) => setKbType(e.target.value)}><Radio value="literature">学术文献</Radio><Radio value="medical_record">病历数据</Radio></Radio.Group>
          </Form.Item>
          {kbType === 'medical_record' && <Form.Item name="field_categories" label="字段分类" initialValue={medicalRecordCategories}><Checkbox.Group options={medicalRecordCategories} /></Form.Item>}
        </Form>
      </Modal>
    </div>
  )
}
