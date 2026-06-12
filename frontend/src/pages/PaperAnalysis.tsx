import { useState, useEffect, useRef } from 'react'
import {
  Typography,
  Table,
  Button,
  Card,
  Row,
  Col,
  Progress,
  Tag,
  Spin,
  Alert,
  message,
  List,
} from 'antd'
import { SafetyCertificateOutlined, DatabaseOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { knowledgeBasesApi, KnowledgeBase } from '@/api/knowledgeBases'
import { documentsApi, DocumentItem } from '@/api/documents'
import { paperAnalysisApi, PaperAnalysisResult } from '@/api/paperAnalysis'
import DocumentDetail from '@/components/documents/DocumentDetail'

const { Title, Paragraph, Text } = Typography

function getRiskColor(score: number): string {
  if (score < 30) return '#52c41a'
  if (score < 60) return '#fa8c16'
  if (score < 80) return '#f5222d'
  return '#820014'
}

function getRiskLevelLabel(level: string | null): { label: string; color: string } {
  switch (level) {
    case 'low':
      return { label: '低', color: 'success' }
    case 'medium':
      return { label: '中', color: 'warning' }
    case 'high':
      return { label: '高', color: 'error' }
    case 'critical':
      return { label: '极高', color: 'default' }
    default:
      return { label: '未知', color: 'default' }
  }
}

function parseFindings(raw: string | null): string[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) return parsed as string[]
    return []
  } catch {
    return []
  }
}

interface DimensionCardProps {
  title: string
  score: number | null
  verdict: string | null
  findingsRaw: string | null
}

function DimensionCard({ title, score, verdict, findingsRaw }: DimensionCardProps) {
  const findings = parseFindings(findingsRaw)
  const hasScore = score !== null && score !== undefined
  const displayScore = hasScore ? score : 0
  const color = getRiskColor(displayScore)

  return (
    <Card title={title} size="small" style={{ height: '100%' }}>
      <div style={{ textAlign: 'center', marginBottom: 12 }}>
        <Progress
          type="circle"
          percent={displayScore}
          strokeColor={hasScore ? color : '#d9d9d9'}
          format={(p) => <span style={{ color: hasScore ? color : '#999' }}>{hasScore ? p : '-'}</span>}
        />
        {verdict && (
          <div style={{ marginTop: 8 }}>
            <Text strong style={{ color, fontSize: 13 }}>{verdict}</Text>
          </div>
        )}
      </div>
      {findings.length > 0 && (
        <ul style={{ paddingLeft: 16, margin: 0 }}>
          {findings.map((f, i) => (
            <li key={i} style={{ marginBottom: 4 }}>
              {f.includes('异常') || f.includes('造假') || f.includes('伪造') || f.includes('风险') ? (
                <Tag color="red" style={{ marginRight: 4 }}>警告</Tag>
              ) : null}
              <Text>{f}</Text>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

interface AnalysisResultViewProps {
  result: PaperAnalysisResult
}

function AnalysisResultView({ result }: AnalysisResultViewProps) {
  const hasOverallScore = result.overall_risk_score !== null && result.overall_risk_score !== undefined
  const overallScore = result.overall_risk_score ?? 0
  const overallColor = getRiskColor(overallScore)
  const riskBadge = getRiskLevelLabel(result.risk_level)

  const recommendations = result.recommendations
    ? (() => { try { return JSON.parse(result.recommendations) } catch { return result.recommendations.split('\n').filter((l: string) => l.trim()) } })()
    : []

  return (
    <div style={{ marginTop: 24 }}>
      <Title level={5} style={{ marginBottom: 16 }}>分析结果</Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <DimensionCard title="数据与统计分析" score={result.data_statistics_score} verdict={result.data_statistics_verdict} findingsRaw={result.data_statistics_findings} />
        </Col>
        <Col xs={24} md={8}>
          <DimensionCard title="逻辑一致性分析" score={result.logic_consistency_score} verdict={result.logic_consistency_verdict} findingsRaw={result.logic_consistency_findings} />
        </Col>
        <Col xs={24} md={8}>
          <DimensionCard title="外部可信度信号" score={result.credibility_score} verdict={result.credibility_verdict} findingsRaw={result.credibility_findings} />
        </Col>
        <Col xs={24} md={8}>
          <DimensionCard title="复现性分析" score={result.reproducibility_score} verdict={result.reproducibility_verdict} findingsRaw={result.reproducibility_findings} />
        </Col>
        <Col xs={24} md={8}>
          <DimensionCard title="图表-文本一致性" score={result.figure_consistency_score} verdict={result.figure_consistency_verdict} findingsRaw={result.figure_consistency_findings} />
        </Col>
        <Col xs={24} md={8}>
          <DimensionCard title="引用操纵检测" score={result.citation_manipulation_score} verdict={result.citation_manipulation_verdict} findingsRaw={result.citation_manipulation_findings} />
        </Col>

        <Col xs={24}>
          <Card title="综合风险评估">
            <Row gutter={24} align="middle">
              <Col xs={24} sm={8} style={{ textAlign: 'center' }}>
                <Progress type="circle" percent={overallScore} strokeColor={hasOverallScore ? overallColor : '#d9d9d9'} format={(p) => <span style={{ color: hasOverallScore ? overallColor : '#999' }}>{hasOverallScore ? p : '-'}</span>} size={120} />
                <div style={{ marginTop: 8 }}>
                  <Text>风险等级：</Text>
                  <Tag color={riskBadge.color === 'default' ? '#820014' : riskBadge.color} style={riskBadge.color === 'default' ? { color: '#fff', borderColor: '#820014' } : {}}>
                    {riskBadge.label}
                  </Tag>
                </div>
              </Col>
              <Col xs={24} sm={16}>
                {result.overall_summary && (
                  <div style={{ marginBottom: 12 }}>
                    <Text strong>综合评估：</Text>
                    <Paragraph style={{ marginTop: 4, marginBottom: 0 }}>{result.overall_summary}</Paragraph>
                  </div>
                )}
                {recommendations.length > 0 && (
                  <div>
                    <Text strong>处理建议：</Text>
                    <ol style={{ paddingLeft: 20, marginTop: 4, marginBottom: 0 }}>
                      {recommendations.map((r: string, i: number) => <li key={i}>{r}</li>)}
                    </ol>
                  </div>
                )}
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default function PaperAnalysis() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [docsLoading, setDocsLoading] = useState(false)
  const [docsPage, setDocsPage] = useState(1)
  const [docsTotal, setDocsTotal] = useState(0)

  const [analyzingDocId, setAnalyzingDocId] = useState<string | null>(null)
  const [result, setResult] = useState<PaperAnalysisResult | null>(null)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [viewDocId, setViewDocId] = useState<string | null>(null)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    knowledgeBasesApi.list().then((res) => setKbs(res.data))
  }, [])

  useEffect(() => {
    if (!selectedKb) {
      setDocuments([])
      setDocsTotal(0)
      return
    }
    setDocsLoading(true)
    documentsApi
      .list({ knowledge_base_id: selectedKb.id, page: docsPage, page_size: 10 })
      .then((res) => {
        setDocuments(res.data.items)
        setDocsTotal(res.data.total)
      })
      .finally(() => setDocsLoading(false))
  }, [selectedKb, docsPage])

  useEffect(() => {
    setDocsPage(1)
  }, [selectedKb?.id])

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const startPolling = (documentId: string) => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const res = await paperAnalysisApi.get(documentId)
        const data = res.data
        if (data.status === 'completed' || data.status === 'failed') {
          stopPolling()
          setResult(data)
          setAnalyzingDocId(null)
          if (data.status === 'failed') {
            setAnalysisError(data.error_message ?? '分析失败，请重试')
          }
        }
      } catch {
        stopPolling()
        setAnalyzingDocId(null)
        setAnalysisError('获取分析结果失败，请重试')
      }
    }, 3000)
  }

  const handleStartAnalysis = async (documentId: string) => {
    setAnalyzingDocId(documentId)
    setResult(null)
    setAnalysisError(null)
    stopPolling()

    try {
      const res = await paperAnalysisApi.trigger(documentId)
      const data = res.data
      if (data.status === 'completed') {
        setResult(data)
        setAnalyzingDocId(null)
      } else if (data.status === 'failed') {
        setAnalyzingDocId(null)
        setAnalysisError(data.error_message ?? '分析失败，请重试')
      } else {
        startPolling(documentId)
      }
    } catch {
      setAnalyzingDocId(null)
      message.error('启动分析失败，请重试')
    }
  }

  const columns: ColumnsType<DocumentItem> = [
    {
      title: '文档标题',
      dataIndex: 'title',
      ellipsis: true,
      render: (title: string, record) => (
        <a onClick={() => setViewDocId(record.id)} style={{ cursor: 'pointer' }}>{title}</a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'file_type',
      width: 80,
      render: (v: string) => <Tag>{v.toUpperCase()}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (v: string) => {
        const map: Record<string, string> = { indexed: 'success', processing: 'processing', failed: 'error', uploaded: 'default' }
        return <Tag color={map[v] ?? 'default'}>{v}</Tag>
      },
    },
    {
      title: '操作',
      width: 120,
      render: (_, record) => {
        const isAnalyzing = analyzingDocId === record.id
        const hasResult = result?.document_id === record.id
        return (
          <Button
            type="primary"
            size="small"
            icon={<SafetyCertificateOutlined />}
            loading={isAnalyzing}
            disabled={!!analyzingDocId && !isAnalyzing}
            onClick={() => handleStartAnalysis(record.id)}
          >
            {hasResult ? '重新分析' : '开始分析'}
          </Button>
        )
      },
    },
  ]

  // 知识库卡片列表
  if (!selectedKb) {
    return (
      <div>
        <Title level={4}>论文鉴真</Title>
        <List
          grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 3 }}
          dataSource={kbs}
          renderItem={(kb) => (
            <List.Item>
              <Card
                hoverable
                onClick={() => setSelectedKb(kb)}
                style={{ cursor: 'pointer' }}
              >
                <Card.Meta
                  avatar={<DatabaseOutlined style={{ fontSize: 28, color: '#1677ff' }} />}
                  title={kb.name}
                  description={
                    <>
                      <Text type="secondary">{kb.description || '暂无描述'}</Text>
                      <div style={{ marginTop: 8 }}>
                        <Tag>{kb.document_count} 篇文档</Tag>
                      </div>
                    </>
                  }
                />
              </Card>
            </List.Item>
          )}
        />
      </div>
    )
  }

  // 论文列表 + 分析结果
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => { setSelectedKb(null); setResult(null); setAnalysisError(null) }} style={{ marginRight: 12 }} />
        <Title level={4} style={{ margin: 0 }}>{selectedKb.name} - 论文鉴真</Title>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={documents}
          loading={docsLoading}
          pagination={{
            current: docsPage,
            total: docsTotal,
            pageSize: 10,
            showSizeChanger: false,
            onChange: setDocsPage,
          }}
          size="small"
        />
      </Card>

      {analyzingDocId && !result && (
        <Card>
          <div style={{ textAlign: 'center', padding: 48 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}><Text type="secondary">正在分析中...</Text></div>
          </div>
        </Card>
      )}

      {analysisError && (
        <Alert type="error" showIcon message="分析失败" description={analysisError} style={{ marginBottom: 16 }} />
      )}

      {result && result.status === 'completed' && <AnalysisResultView result={result} />}

      <DocumentDetail documentId={viewDocId} open={!!viewDocId} onClose={() => setViewDocId(null)} />
    </div>
  )
}
