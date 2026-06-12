import { useEffect, useMemo, useState } from 'react'
import { Badge, Button, Card, Col, Empty, Form, Input, List, Modal, Pagination, Progress, Row, Select, Space, Spin, Switch, Tag, Typography, message } from 'antd'
import { BulbOutlined, FileTextOutlined, PlusOutlined, ReloadOutlined, SafetyCertificateOutlined, SearchOutlined, SyncOutlined } from '@ant-design/icons'
import { frontierApi, FocusPoint, FrontierPaper } from '@/api/frontier'
import { knowledgeBasesApi, KnowledgeBase } from '@/api/knowledgeBases'
import { paperAnalysisApi } from '@/api/paperAnalysis'
import DocumentDetail from '@/components/documents/DocumentDetail'

const { Title, Text, Paragraph } = Typography

function scoreColor(score: number) {
  if (score >= 75) return '#1677ff'
  if (score >= 55) return '#52c41a'
  if (score >= 35) return '#faad14'
  return '#8c8c8c'
}

function formatDate(value: string | null) {
  return value ? value.slice(0, 10) : '未知日期'
}

function queryTerms(query: string) {
  return query
    .toLowerCase()
    .replace(/[()"]/g, ' ')
    .split(/\s+|\bor\b|\band\b/i)
    .map((term) => term.trim())
    .filter((term) => term.length > 2 && !['and', 'or', 'the', 'with'].includes(term))
}

function FocusCard({ focus, active, onClick }: { focus: FocusPoint; active: boolean; onClick: () => void }) {
  return (
    <Card
      size="small"
      hoverable
      onClick={onClick}
      style={{ marginBottom: 8, borderColor: active ? '#1677ff' : undefined }}
    >
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        <Space style={{ justifyContent: 'space-between', width: '100%' }}>
          <Text strong ellipsis style={{ maxWidth: 190 }}>{focus.name}</Text>
          <Tag>{focus.source_type}</Tag>
        </Space>
        <Text type="secondary" style={{ fontSize: 12 }}>{focus.query || '未设置关键词'}</Text>
        <Space wrap size={6}>
          {focus.knowledge_base_name && <Tag color="green">{focus.knowledge_base_name}</Tag>}
          {focus.sync_status && <Tag color={focus.sync_status === 'running' ? 'processing' : focus.sync_status === 'failed' ? 'error' : 'default'}>{focus.sync_status}</Tag>}
          {focus.cron_expr && <Tag color="blue">{focus.cron_expr}</Tag>}
          <Text type="secondary" style={{ fontSize: 12 }}>每次 {focus.max_results} 篇</Text>
        </Space>
        {focus.last_message && <Text type="secondary" style={{ fontSize: 12 }}>{focus.last_message}</Text>}
      </Space>
    </Card>
  )
}

function PaperItem({ paper, onOpen, onAnalyze }: { paper: FrontierPaper; onOpen: () => void; onAnalyze: () => void }) {
  return (
    <Card size="small" style={{ marginBottom: 10 }}>
      <Row gutter={16} align="top">
        <Col flex="84px">
          <Progress
            type="circle"
            percent={paper.frontier_score}
            size={64}
            strokeColor={scoreColor(paper.frontier_score)}
            format={(value) => <span style={{ color: scoreColor(paper.frontier_score), fontSize: 14 }}>{value}</span>}
          />
        </Col>
        <Col flex="auto">
          <Space direction="vertical" size={6} style={{ width: '100%' }}>
            <Space wrap>
              <Tag color={paper.status === 'indexed' ? 'success' : 'default'}>{paper.status}</Tag>
              <Tag color="geekblue">{paper.recommendation}</Tag>
              <Tag color="purple">相关性 {paper.relevance_score}</Tag>
              {paper.analysis_risk_score !== null && paper.analysis_risk_score !== undefined && (
                <Tag color={paper.analysis_risk_score >= 60 ? 'error' : paper.analysis_risk_score >= 30 ? 'warning' : 'success'}>
                  真实性风险 {paper.analysis_risk_score}
                </Tag>
              )}
              {paper.source_type && <Tag>{paper.source_type}</Tag>}
              <Text type="secondary">{formatDate(paper.publication_date)}</Text>
              <Text type="secondary">{paper.knowledge_base_name}</Text>
            </Space>
            <a onClick={onOpen} style={{ fontWeight: 600, fontSize: 15 }}>{paper.title}</a>
            <Text type="secondary" ellipsis>{paper.authors || 'Unknown authors'}</Text>
            {paper.abstract && <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 0 }}>{paper.abstract}</Paragraph>}
            <Space wrap>
              {paper.reasons.map((reason) => <Tag key={reason} color="blue">{reason}</Tag>)}
            </Space>
            <Space>
              <Button size="small" icon={<FileTextOutlined />} onClick={onOpen}>查看论文</Button>
              <Button size="small" icon={<SafetyCertificateOutlined />} onClick={onAnalyze}>论文鉴真</Button>
            </Space>
          </Space>
        </Col>
      </Row>
    </Card>
  )
}

export default function FrontierDiscovery() {
  const [focusPoints, setFocusPoints] = useState<FocusPoint[]>([])
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [papers, setPapers] = useState<FrontierPaper[]>([])
  const [trends, setTrends] = useState<{ keyword: string; count: number }[]>([])
  const [activeFocusId, setActiveFocusId] = useState<string | undefined>()
  const [days, setDays] = useState(90)
  const [status, setStatus] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')
  const [sortBy, setSortBy] = useState<'time' | 'risk' | 'relevance'>('time')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [viewDocId, setViewDocId] = useState<string | null>(null)
  const [focusOpen, setFocusOpen] = useState(false)
  const [kbFocusOpen, setKbFocusOpen] = useState(false)
  const [focusForm] = Form.useForm()
  const [kbFocusForm] = Form.useForm()

  const fetchData = async () => {
    setLoading(true)
    try {
      const currentFocus = focusPoints.find((focus) => focus.id === activeFocusId)
      const res = await frontierApi.list({
        days,
        status,
        limit: 200,
        kb_id: currentFocus?.knowledge_base_id || undefined,
      })
      setPapers(res.data.papers)
      setTrends(res.data.trends)
      const focusRes = await frontierApi.listFocusPoints()
      setFocusPoints(focusRes.data)
    } catch {
      message.error('获取前沿论文失败，请确认登录状态后重试')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    knowledgeBasesApi.list()
      .then((res) => setKbs(res.data))
      .catch(() => message.error('获取知识库列表失败，请确认登录状态后重试'))
  }, [days, status, activeFocusId])

  const filteredPapers = useMemo(() => {
    const q = keyword.trim().toLowerCase()
    const activeFocus = focusPoints.find((focus) => focus.id === activeFocusId)
    const terms = activeFocus ? queryTerms(activeFocus.query) : []
    const filtered = papers.filter((paper) => {
      if (activeFocus?.knowledge_base_id && paper.knowledge_base_id !== activeFocus.knowledge_base_id) return false
      const text = [paper.title, paper.abstract || '', paper.authors || '', paper.journal || ''].join(' ').toLowerCase()
      if (!activeFocus?.knowledge_base_id && terms.length > 0 && !terms.some((term) => text.includes(term))) return false
      if (!q) return true
      return text.includes(q)
    })
    return [...filtered].sort((a, b) => {
      if (sortBy === 'risk') {
        return (b.analysis_risk_score ?? -1) - (a.analysis_risk_score ?? -1)
      }
      if (sortBy === 'relevance') {
        return b.relevance_score - a.relevance_score
      }
      const aTime = new Date(a.publication_date || a.created_at).getTime()
      const bTime = new Date(b.publication_date || b.created_at).getTime()
      return bTime - aTime
    })
  }, [keyword, papers, focusPoints, activeFocusId, sortBy])

  const activeTrends = useMemo(() => {
    const stopwords = new Set(['the', 'and', 'for', 'with', 'from', 'that', 'this', 'into', 'using', 'study', 'research', 'analysis', 'patient', 'patients', 'clinical'])
    const counts = new Map<string, number>()
    filteredPapers.forEach((paper) => {
      const text = `${paper.title} ${paper.abstract || ''}`.toLowerCase()
      const matches = text.match(/[a-z][a-z-]{3,}/g) || []
      matches.forEach((word) => {
        if (!stopwords.has(word)) counts.set(word, (counts.get(word) || 0) + 1)
      })
    })
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)
      .map(([keyword, count]) => ({ keyword, count }))
  }, [filteredPapers])

  const pageSize = 10
  const pagedPapers = filteredPapers.slice((page - 1) * pageSize, page * pageSize)
  const activeFocus = focusPoints.find((focus) => focus.id === activeFocusId)
  const rangeStart = filteredPapers.length === 0 ? 0 : (page - 1) * pageSize + 1
  const rangeEnd = Math.min(page * pageSize, filteredPapers.length)

  const paperPager = (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '8px 0 12px' }}>
      <Text type="secondary">当前 {rangeStart}-{rangeEnd} / 共 {filteredPapers.length} 篇</Text>
      <Pagination
        current={page}
        pageSize={pageSize}
        total={filteredPapers.length}
        onChange={setPage}
        showSizeChanger={false}
        size="small"
      />
    </div>
  )

  useEffect(() => {
    setPage(1)
  }, [keyword, activeFocusId, days, status, sortBy])

  const createFocus = async (values: { name: string; query: string; source_type: string; max_results?: number; cron_expr?: string; auto_sync?: boolean }) => {
    const res = await frontierApi.createFocusPoint({
      name: values.name,
      query: values.query,
      source_type: values.source_type,
      max_results: values.max_results || 50,
      cron_expr: values.cron_expr,
      auto_sync: values.auto_sync !== false,
    })
    setFocusPoints((prev) => [res.data, ...prev])
    setActiveFocusId(res.data.id)
    setFocusOpen(false)
    focusForm.resetFields()
    message.success(res.data.sync_task_id ? '关注点已创建，正在下载论文' : '关注点已创建')
  }

  const createFocusFromKb = async (values: { knowledge_base_id: string; name?: string; query: string; source_type?: string; max_results?: number; cron_expr?: string }) => {
    const kb = kbs.find((item) => item.id === values.knowledge_base_id)
    if (!kb) return
    const res = await frontierApi.createFocusPoint({
      name: values.name || kb.name,
      query: values.query,
      source_type: values.source_type || 'pmc',
      knowledge_base_id: kb.id,
      max_results: values.max_results || 50,
      cron_expr: values.cron_expr,
      auto_sync: true,
    })
    setFocusPoints((prev) => [res.data, ...prev])
    setActiveFocusId(res.data.id)
    setKbFocusOpen(false)
    kbFocusForm.resetFields()
    message.success('已创建关注点并开始下载论文')
  }

  const createKnowledgeBaseFromFocus = async () => {
    if (!activeFocus) return
    const res = await frontierApi.createFocusPoint({
      name: activeFocus.name,
      query: activeFocus.query,
      source_type: activeFocus.source_type,
      max_results: activeFocus.max_results,
      cron_expr: activeFocus.cron_expr || undefined,
      auto_sync: true,
    })
    await frontierApi.deleteFocusPoint(activeFocus.id)
    setFocusPoints((prev) => [res.data, ...prev.filter((focus) => focus.id !== activeFocus.id)])
    setActiveFocusId(res.data.id)
    message.success('已创建知识库和同步任务')
  }

  const deleteFocus = () => {
    if (!activeFocus) return
    frontierApi.deleteFocusPoint(activeFocus.id).catch(() => {})
    setFocusPoints((prev) => prev.filter((focus) => focus.id !== activeFocus.id))
    setActiveFocusId(undefined)
  }

  const focusMatchedPapers = useMemo(() => {
    if (!activeFocus) return []
    const terms = queryTerms(activeFocus.query)
    return papers.filter((paper) =>
      [paper.title, paper.abstract || '', paper.authors || '', paper.journal || '']
        .join(' ')
        .toLowerCase()
        .split(/\s+/)
        .some((word) => terms.includes(word))
    )
  }, [activeFocus, papers])

  const handleAnalyze = async (paper: FrontierPaper) => {
    await paperAnalysisApi.trigger(paper.document_id)
    setViewDocId(paper.document_id)
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ marginBottom: 4 }}><BulbOutlined /> 前沿发现</Title>
          <Text type="secondary">自定义关注点，持续追踪相关前沿论文；可从关注点创建知识库和同步任务。</Text>
        </div>
        <Button icon={<ReloadOutlined />} onClick={fetchData}>刷新</Button>
      </div>

      <Row gutter={16}>
        <Col xs={24} lg={6}>
          <Card
            title="关注点"
            size="small"
            style={{ marginBottom: 16 }}
            extra={<Button size="small" icon={<PlusOutlined />} onClick={() => setFocusOpen(true)}>新增</Button>}
          >
            <Space direction="vertical" style={{ width: '100%', marginBottom: 8 }}>
              <Button block type={!activeFocusId ? 'primary' : 'default'} onClick={() => setActiveFocusId(undefined)}>全部论文</Button>
              <Button block onClick={() => setKbFocusOpen(true)}>从知识库创建关注点</Button>
            </Space>
            <div style={{ maxHeight: 'calc(100vh - 280px)', overflow: 'auto' }}>
              {focusPoints.map((focus) => (
                <FocusCard key={focus.id} focus={focus} active={focus.id === activeFocusId} onClick={() => setActiveFocusId(focus.id)} />
              ))}
              {focusPoints.length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无关注点" />}
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            size="small"
            title={activeFocus ? activeFocus.name : '推荐论文'}
            extra={<Badge count={filteredPapers.length} overflowCount={999} />}
          >
            <Space wrap style={{ marginBottom: 12 }}>
              <Input
                allowClear
                prefix={<SearchOutlined />}
                placeholder="在推荐结果内筛选"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                style={{ width: 240 }}
              />
              <Select
                value={days}
                onChange={setDays}
                style={{ width: 130 }}
                options={[
                  { value: 30, label: '近 30 天' },
                  { value: 90, label: '近 90 天' },
                  { value: 180, label: '近 180 天' },
                  { value: 365, label: '近 1 年' },
                ]}
              />
              <Select
                allowClear
                placeholder="索引状态"
                value={status}
                onChange={setStatus}
                style={{ width: 130 }}
                options={[
                  { value: 'indexed', label: '已索引' },
                  { value: 'uploaded', label: '待索引' },
                  { value: 'failed', label: '索引失败' },
                ]}
              />
              <Select
                value={sortBy}
                onChange={setSortBy}
                style={{ width: 150 }}
                options={[
                  { value: 'time', label: '按时间排序' },
                  { value: 'risk', label: '按真实性风险' },
                  { value: 'relevance', label: '按相关性' },
                ]}
              />
              {activeFocus && !activeFocus.knowledge_base_id && (
                <Button type="primary" onClick={createKnowledgeBaseFromFocus}>由关注点创建知识库</Button>
              )}
              {activeFocus && <Button danger onClick={deleteFocus}>删除关注点</Button>}
            </Space>

            <Spin spinning={loading}>
              {paperPager}
              {filteredPapers.length === 0 ? (
                <Empty description="暂无推荐论文" />
              ) : (
                <List
                  dataSource={pagedPapers}
                  renderItem={(paper) => (
                    <PaperItem
                      paper={paper}
                      onOpen={() => setViewDocId(paper.document_id)}
                      onAnalyze={() => handleAnalyze(paper)}
                    />
                  )}
                />
              )}
              {filteredPapers.length > pageSize && paperPager}
            </Spin>
          </Card>
        </Col>

        <Col xs={24} lg={6}>
          <Card size="small" title="趋势关键词" style={{ marginBottom: 16 }}>
            <Space wrap>
              {(activeFocus ? activeTrends : trends).map((trend) => (
                <Tag key={trend.keyword} color="blue">{trend.keyword} · {trend.count}</Tag>
              ))}
            </Space>
          </Card>
          {activeFocus && (
            <Card size="small" title="关注点匹配" style={{ marginBottom: 16 }}>
              <Space direction="vertical" size={6}>
                <Text>关键词：{queryTerms(activeFocus.query).slice(0, 8).join(' / ') || '未设置'}</Text>
                <Text>当前匹配：{filteredPapers.length} 篇</Text>
                <Text>全量粗匹配：{focusMatchedPapers.length} 篇</Text>
              </Space>
            </Card>
          )}
          <Card size="small" title="前沿指数说明">
            <Space direction="vertical" size={8}>
              <Text><SyncOutlined /> 近期发表或近期导入会提高分数。</Text>
              <Text><SafetyCertificateOutlined /> RCT、Meta-analysis、系统综述等证据类型更靠前。</Text>
              <Text><SearchOutlined /> 包含 AI、omics、biomarker 等前沿方法会加权。</Text>
              <Text><FileTextOutlined /> 已索引论文更适合直接问答和精读。</Text>
            </Space>
          </Card>
        </Col>
      </Row>

      <DocumentDetail documentId={viewDocId} open={!!viewDocId} onClose={() => setViewDocId(null)} />
      <Modal title="新增关注点" open={focusOpen} onCancel={() => setFocusOpen(false)} onOk={() => focusForm.submit()}>
        <Form form={focusForm} layout="vertical" onFinish={createFocus} initialValues={{ source_type: 'pmc', max_results: 50, cron_expr: '0 8 * * *', auto_sync: true }}>
          <Form.Item name="name" label="关注点名称" rules={[{ required: true }]}><Input placeholder="例如：心血管代谢与炎症" /></Form.Item>
          <Form.Item name="query" label="检索关键词" rules={[{ required: true }]}><Input.TextArea rows={3} placeholder='例如：("heart failure" OR atherosclerosis) AND biomarker' /></Form.Item>
          <Form.Item name="source_type" label="默认数据源"><Select options={[{ value: 'pmc', label: 'PMC' }, { value: 'europepmc', label: 'Europe PMC' }, { value: 'biorxiv', label: 'bioRxiv/medRxiv' }, { value: 'semantic_scholar', label: 'Semantic Scholar' }, { value: 'arxiv', label: 'arXiv' }]} /></Form.Item>
          <Form.Item name="max_results" label="每次下载数量"><Select options={[10, 20, 50, 100].map((value) => ({ value, label: `${value} 篇` }))} /></Form.Item>
          <Form.Item name="cron_expr" label="定时表达式"><Input placeholder="0 8 * * *" /></Form.Item>
          <Form.Item name="auto_sync" label="创建后立即下载论文" valuePropName="checked"><Switch /></Form.Item>
        </Form>
      </Modal>
      <Modal title="从知识库创建关注点" open={kbFocusOpen} onCancel={() => setKbFocusOpen(false)} onOk={() => kbFocusForm.submit()}>
        <Form form={kbFocusForm} layout="vertical" onFinish={createFocusFromKb} initialValues={{ source_type: 'pmc', max_results: 50 }}>
          <Form.Item name="knowledge_base_id" label="知识库" rules={[{ required: true }]}><Select options={kbs.map((kb) => ({ value: kb.id, label: kb.name }))} /></Form.Item>
          <Form.Item name="name" label="关注点名称"><Input placeholder="默认使用知识库名称" /></Form.Item>
          <Form.Item name="query" label="检索关键词" rules={[{ required: true }]}><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="source_type" label="默认数据源"><Select options={[{ value: 'pmc', label: 'PMC' }, { value: 'europepmc', label: 'Europe PMC' }, { value: 'biorxiv', label: 'bioRxiv/medRxiv' }, { value: 'semantic_scholar', label: 'Semantic Scholar' }, { value: 'arxiv', label: 'arXiv' }]} /></Form.Item>
          <Form.Item name="max_results" label="每次下载数量"><Select options={[10, 20, 50, 100].map((value) => ({ value, label: `${value} 篇` }))} /></Form.Item>
          <Form.Item name="cron_expr" label="定时表达式"><Input placeholder="例如：0 8 * * *" /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
