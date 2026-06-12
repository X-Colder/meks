import { useState, useEffect, useRef } from 'react'
import { Button, Input, List, Typography, Space, message, Modal, Card, Tabs, Spin, Empty } from 'antd'
import {
  PlusOutlined, DeleteOutlined, FileTextOutlined, FolderOutlined,
  SendOutlined, CopyOutlined, ExportOutlined,
} from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import { papersApi, Paper, PaperDetail, PaperBlock } from '@/api/papers'
import '@/styles/chat-markdown.css'

const { Title, Text } = Typography

function normalizeMarkdown(content: string): string {
  return content
    .replace(/(^|\n)(\s*)(\d+)\.\s*\n{1,2}(?=\S)/g, '$1$2$3. ')
    .replace(/(^|\n)(\s*)([-*+])\s*\n{1,2}(?=\S)/g, '$1$2$3 ')
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

function AIWritingChat({ paperId, blocks, onInsertDraft }: { paperId: string; blocks: PaperBlock[]; onInsertDraft: (content: string, mode: 'append' | 'replace') => void }) {
  const storageKey = `meks-paper-chat:${paperId}`
  const initialMessages = (): { role: string; content: string }[] => {
    try {
      const saved = localStorage.getItem(storageKey)
      if (saved) return JSON.parse(saved)
    } catch {
      // ignore corrupt local history
    }
    return [
      { role: 'assistant', content: '我是你的论文研究助手。你可以持续向我询问研究背景、前沿进展、方法设计、论证思路、段落润色建议。我会保留本次论文的对话记录；你可以选中我的答复片段，插入右侧草稿。' },
    ]
  }
  const [messages, setMessages] = useState<{ role: string; content: string }[]>(initialMessages)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(messages))
  }, [messages, storageKey])

  const getToken = () => {
    try { return JSON.parse(localStorage.getItem('meks-auth') || '{}').state?.accessToken || '' }
    catch { return '' }
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const userMsg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)

    try {
      const materials = blocks.filter(b => b.source_type).map(b => b.content).join('\n\n---\n\n')
      const currentDoc = blocks.find(b => b.block_type === 'text' && !b.source_type)?.content || ''

      const history = messages.slice(-8).map(m => `${m.role === 'user' ? '用户' : '助手'}：${m.content}`).join('\n\n')
      const prompt = `你是一位医学论文研究助手，目标是帮助用户形成论文选题、研究设计、论证思路、文献综述视角和可引用的写作素材。

已收集的参考素材（共${blocks.filter(b => b.source_type).length}条）：
${materials.slice(0, 8000) || '（暂无素材）'}

当前论文草稿：
${currentDoc.slice(0, 4000) || '（暂无草稿）'}

最近对话：
${history || '（暂无历史对话）'}

用户要求：${userMsg}

请直接回答用户当前问题。不要默认生成完整论文；优先给出分析、建议、结构化思路、可选写作片段或下一步行动。若需要给出可写入论文的内容，请标明“可写入草稿片段”。使用清晰的 Markdown。`

      const token = getToken()
      const sessionRes = await fetch('/api/v1/chat/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ knowledge_base_ids: [] }),
      })
      const session = await sessionRes.json()

      const msgRes = await fetch(`/api/v1/chat/sessions/${session.id}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ content: prompt }),
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
        }
      }

      setMessages(prev => [...prev, { role: 'assistant', content: fullResponse || '生成失败，请重试' }])
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: '请求失败，请重试' }])
    } finally {
      setLoading(false)
    }
  }

  const insertSelection = (content: string, mode: 'append' | 'replace') => {
    const selected = window.getSelection()?.toString().trim()
    onInsertDraft(selected || content, mode)
  }

  const clearHistory = () => {
    const next = initialMessages().slice(0, 1)
    setMessages(next)
    localStorage.setItem(storageKey, JSON.stringify(next))
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '8px 12px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Text type="secondary" style={{ fontSize: 12 }}>AI 对话记录保存在当前浏览器；可选中答复片段后插入草稿。</Text>
        <Button size="small" onClick={clearHistory}>清空对话</Button>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 12 }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ marginBottom: 12, textAlign: msg.role === 'user' ? 'right' : 'left' }}>
            <div style={{
              display: 'inline-block', maxWidth: '85%', padding: '10px 14px', borderRadius: 12,
              background: msg.role === 'user' ? '#1677ff' : '#f5f5f5',
              color: msg.role === 'user' ? '#fff' : '#333',
            }}>
              {msg.role === 'user' ? (
                <Text style={{ color: '#fff', whiteSpace: 'pre-wrap', fontSize: 13 }}>{msg.content}</Text>
              ) : (
                <>
                  <div className="chat-markdown" style={{ fontSize: 13, lineHeight: 1.8 }}>
                    <ReactMarkdown>{normalizeMarkdown(msg.content)}</ReactMarkdown>
                  </div>
                  {i > 0 && msg.content && msg.content !== '请求失败，请重试' && (
                    <Space style={{ marginTop: 8 }}>
                      <Button size="small" onClick={() => insertSelection(msg.content, 'append')}>插入选中/全文</Button>
                      <Button size="small" onClick={() => insertSelection(msg.content, 'replace')}>替换为选中/全文</Button>
                    </Space>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        {loading && <div><Spin size="small" /> <Text type="secondary">AI 正在撰写中...</Text></div>}
        <div ref={chatEndRef} />
      </div>
      <div style={{ padding: '8px 12px', borderTop: '1px solid #f0f0f0' }}>
        <Input.Search
          placeholder="描述你的需求，如：根据素材写一篇关于心血管疾病的综述..."
          enterButton={<><SendOutlined /> 发送</>}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onSearch={handleSend}
          loading={loading}
        />
      </div>
    </div>
  )
}

function DraftEditor({ content, onSave }: { content: string; onSave: (content: string) => Promise<void> }) {
  const [draft, setDraft] = useState(content)
  const [saving, setSaving] = useState(false)

  useEffect(() => setDraft(content), [content])

  const save = async () => {
    setSaving(true)
    try {
      await onSave(draft)
      message.success('草稿已保存')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, height: 'calc(100vh - 220px)' }}>
      <Card size="small" title="可编辑草稿" extra={<Button type="primary" size="small" loading={saving} onClick={save}>保存草稿</Button>}>
        <Input.TextArea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="在这里编辑正式论文草稿。AI 的回复不会自动覆盖这里，需手动插入或替换。"
          style={{ height: 'calc(100vh - 300px)', resize: 'none', fontFamily: 'Menlo, Consolas, monospace', lineHeight: 1.7 }}
        />
      </Card>
      <Card size="small" title="实时预览">
        <div className="chat-markdown" style={{ height: 'calc(100vh - 300px)', overflow: 'auto', lineHeight: 1.9 }}>
          {draft.trim() ? <ReactMarkdown>{normalizeMarkdown(draft)}</ReactMarkdown> : <Empty description="暂无草稿内容" />}
        </div>
      </Card>
    </div>
  )
}

function DraftPanel({ content, onSave }: { content: string; onSave: (content: string) => Promise<void> }) {
  const [draft, setDraft] = useState(content)
  const [saving, setSaving] = useState(false)

  useEffect(() => setDraft(content), [content])

  const save = async () => {
    setSaving(true)
    try {
      await onSave(draft)
      message.success('草稿已保存')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card
      size="small"
      title="正式草稿"
      extra={<Button type="primary" size="small" loading={saving} onClick={save}>保存</Button>}
      style={{ height: '100%' }}
      bodyStyle={{ height: 'calc(100% - 48px)', padding: 12 }}
    >
      <Input.TextArea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="在这里编辑正式论文草稿。左侧 AI 回复不会自动覆盖这里，你可以选中 AI 答复片段后插入。"
        style={{ height: '100%', resize: 'none', fontFamily: 'Menlo, Consolas, monospace', lineHeight: 1.7 }}
      />
    </Card>
  )
}

function DocumentPreview({ paper, content }: { paper: PaperDetail; content: string }) {
  const [exportOpen, setExportOpen] = useState(false)
  const [exportType, setExportType] = useState<'word' | 'pdf'>('word')
  const [watermarkText, setWatermarkText] = useState('')
  const [exporting, setExporting] = useState(false)

  if (!content) return <Empty description="AI 尚未生成论文内容，请在对话中提出写作需求" />

  const openExport = (type: 'word' | 'pdf') => {
    setExportType(type)
    setWatermarkText('')
    setExportOpen(true)
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const response = exportType === 'word'
        ? await papersApi.exportWord(paper.id, watermarkText.trim())
        : await papersApi.exportPdf(paper.id, watermarkText.trim())
      const ext = exportType === 'word' ? 'docx' : 'pdf'
      downloadBlob(response.data as Blob, `${paper.title || 'paper'}.${ext}`)
      message.success('导出完成')
      setExportOpen(false)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div style={{ padding: '24px 32px', maxWidth: 800, margin: '0 auto' }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
        <Button icon={<CopyOutlined />} onClick={() => { navigator.clipboard.writeText(content); message.success('已复制到剪贴板') }}>复制</Button>
        <Button icon={<ExportOutlined />} onClick={() => openExport('word')}>导出 Word</Button>
        <Button icon={<ExportOutlined />} onClick={() => openExport('pdf')}>导出 PDF</Button>
      </div>
      <div className="chat-markdown" style={{ background: '#fff', padding: '32px 40px', borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,0.05)', lineHeight: 2, fontSize: 14 }}>
        <ReactMarkdown>{normalizeMarkdown(content)}</ReactMarkdown>
      </div>
      <Modal
        title={exportType === 'word' ? '导出 Word' : '导出 PDF'}
        open={exportOpen}
        onCancel={() => setExportOpen(false)}
        onOk={handleExport}
        confirmLoading={exporting}
        okText="导出"
      >
        <Input
          placeholder="医院水印文字，例如：XX医院，仅内部使用"
          value={watermarkText}
          onChange={(e) => setWatermarkText(e.target.value)}
          onPressEnter={handleExport}
        />
      </Modal>
    </div>
  )
}

function PaperWorkspace({ paper, onBack }: { paper: PaperDetail; onBack: () => void }) {
  const [blocks, setBlocks] = useState<PaperBlock[]>(paper.blocks || [])
  const [splitPercent, setSplitPercent] = useState(() => {
    const saved = Number(localStorage.getItem(`meks-paper-split:${paper.id}`))
    return Number.isFinite(saved) && saved >= 30 && saved <= 70 ? saved : 56
  })
  const splitRef = useRef<HTMLDivElement>(null)
  const draggingSplit = useRef(false)
  const draftBlock = blocks.find(b => b.block_type === 'text' && !b.source_type)
  const draftContent = draftBlock?.content || ''

  useEffect(() => {
    localStorage.setItem(`meks-paper-split:${paper.id}`, String(splitPercent))
  }, [paper.id, splitPercent])

  const startSplitDrag = () => { draggingSplit.current = true }
  const stopSplitDrag = () => { draggingSplit.current = false }
  const moveSplit = (e: React.MouseEvent) => {
    if (!draggingSplit.current || !splitRef.current) return
    const rect = splitRef.current.getBoundingClientRect()
    const pct = ((e.clientX - rect.left) / rect.width) * 100
    setSplitPercent(Math.max(30, Math.min(70, pct)))
  }

  const refreshBlocks = async () => {
    const res = await papersApi.get(paper.id)
    setBlocks(res.data.blocks || [])
  }

  const handleSaveDraft = async (content: string) => {
    const existingDoc = blocks.find(b => b.block_type === 'text' && !b.source_type)
    if (existingDoc) {
      await papersApi.updateBlock(paper.id, existingDoc.id, { content })
    } else {
      await papersApi.addBlock(paper.id, { block_type: 'text', content, sort_order: 0 })
    }
    await refreshBlocks()
  }

  const handleInsertDraft = async (content: string, mode: 'append' | 'replace') => {
    const normalized = normalizeMarkdown(content).trim()
    const next = mode === 'replace'
      ? normalized
      : [draftContent.trim(), normalized].filter(Boolean).join('\n\n')
    await handleSaveDraft(next)
    message.success(mode === 'replace' ? '已替换草稿' : '已追加到草稿')
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '10px 20px', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Space>
          <Button onClick={onBack} type="text">← 返回</Button>
          <Title level={5} style={{ margin: 0 }}>{paper.title}</Title>
        </Space>
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        <Tabs
          style={{ height: '100%' }}
          tabBarStyle={{ padding: '0 16px', margin: 0 }}
          items={[
            {
              key: 'chat',
              label: '✍️ AI 写作',
              children: (
                <div
                  ref={splitRef}
                  onMouseMove={moveSplit}
                  onMouseUp={stopSplitDrag}
                  onMouseLeave={stopSplitDrag}
                  style={{ display: 'flex', height: 'calc(100vh - 220px)', padding: 12, gap: 0, userSelect: draggingSplit.current ? 'none' : 'auto' }}
                >
                  <Card size="small" title="AI 研究对话" bodyStyle={{ height: 'calc(100% - 48px)', padding: 0 }} style={{ height: '100%', overflow: 'hidden', width: `${splitPercent}%`, minWidth: 360 }}>
                    <AIWritingChat paperId={paper.id} blocks={blocks} onInsertDraft={handleInsertDraft} />
                  </Card>
                  <div
                    onMouseDown={startSplitDrag}
                    style={{ width: 12, cursor: 'col-resize', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}
                  >
                    <div style={{ width: 4, height: 56, borderRadius: 2, background: '#d9d9d9' }} />
                  </div>
                  <div style={{ height: '100%', width: `${100 - splitPercent}%`, minWidth: 360 }}>
                    <DraftPanel content={draftContent} onSave={handleSaveDraft} />
                  </div>
                </div>
              ),
            },
            {
              key: 'draft',
              label: '📝 草稿编辑',
              children: <DraftEditor content={draftContent} onSave={handleSaveDraft} />,
            },
            {
              key: 'document',
              label: '📄 论文预览',
              children: <div style={{ height: 'calc(100vh - 220px)', overflow: 'auto', background: '#f9f9f9' }}><DocumentPreview paper={paper} content={draftContent} /></div>,
            },
          ]}
        />
      </div>
    </div>
  )
}

export default function PaperEditor() {
  const [papers, setPapers] = useState<Paper[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedPaper, setSelectedPaper] = useState<PaperDetail | null>(null)
  const [createTitle, setCreateTitle] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [paperPage, setPaperPage] = useState(1)

  const fetchPapers = async () => {
    setLoading(true)
    try { const res = await papersApi.list(); setPapers(res.data) }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchPapers() }, [])

  const handleCreate = async () => {
    const res = await papersApi.create({ title: createTitle || '未命名论文' })
    message.success('论文已创建')
    setCreateOpen(false)
    setCreateTitle('')
    setPaperPage(1)
    const detail = await papersApi.get(res.data.id)
    setSelectedPaper(detail.data)
    fetchPapers()
  }

  const handleOpen = async (paper: Paper) => {
    const res = await papersApi.get(paper.id)
    setSelectedPaper(res.data)
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    await papersApi.delete(id)
    message.success('已删除')
    if ((papers.length - 1) <= (paperPage - 1) * 10 && paperPage > 1) setPaperPage(paperPage - 1)
    fetchPapers()
  }

  if (selectedPaper) {
    return <PaperWorkspace paper={selectedPaper} onBack={() => { setSelectedPaper(null); fetchPapers() }} />
  }

  const pageSize = 10
  const pagedPapers = papers.slice((paperPage - 1) * pageSize, paperPage * pageSize)

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 112px)' }}>
      <div style={{ width: 280, borderRight: '1px solid #f0f0f0', padding: 16, overflow: 'auto', background: '#fafafa' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <Title level={5} style={{ margin: 0 }}>我的论文</Title>
          <Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新建</Button>
        </div>
        <List
          loading={loading}
          dataSource={pagedPapers}
          locale={{ emptyText: '暂无论文' }}
          pagination={{
            current: paperPage,
            total: papers.length,
            pageSize,
            size: 'small',
            showSizeChanger: false,
            onChange: setPaperPage,
          }}
          renderItem={(paper) => (
          <div
            onClick={() => handleOpen(paper)}
            style={{ padding: '10px 12px', borderRadius: 8, marginBottom: 4, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', transition: 'background 0.2s' }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#e6f4ff')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            <Space>
              <FileTextOutlined style={{ color: '#1677ff' }} />
              <div>
                <div><Text ellipsis style={{ maxWidth: 150, fontSize: 13 }}>{paper.title}</Text></div>
                <Text type="secondary" style={{ fontSize: 11 }}>{paper.updated_at?.slice(0, 10)}</Text>
              </div>
            </Space>
            <Button type="text" size="small" danger icon={<DeleteOutlined />} onClick={(e) => handleDelete(paper.id, e)} />
          </div>
        )} />
      </div>

      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5' }}>
        <div style={{ textAlign: 'center' }}>
          <FolderOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />
          <div style={{ marginTop: 16 }}><Text type="secondary">选择一篇论文，或创建新论文开始写作</Text></div>
          <div style={{ marginTop: 8 }}><Text type="secondary" style={{ fontSize: 12 }}>在知识库的搜索、问答中点击"引用到论文"收集素材</Text></div>
          <Button type="primary" style={{ marginTop: 16 }} icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新建论文</Button>
        </div>
      </div>

      <Modal title="新建论文" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={handleCreate} okText="创建">
        <Input placeholder="输入论文主题，如：心血管疾病治疗进展综述" value={createTitle} onChange={(e) => setCreateTitle(e.target.value)} onPressEnter={handleCreate} autoFocus />
      </Modal>
    </div>
  )
}
