import { Card, Col, Progress, Row, Tag, Typography } from 'antd'
import { PaperAnalysisResult } from '@/api/paperAnalysis'

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

function parseTextList(raw: string | null): string[] {
  if (!raw) return []
  try {
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed)) return parsed.map((item) => String(item)).filter(Boolean)
    if (typeof parsed === 'string') return parsed.split('\n').map((item) => item.trim()).filter(Boolean)
  } catch {
    return raw.split('\n').map((item) => item.trim()).filter(Boolean)
  }
  return []
}

interface DimensionCardProps {
  title: string
  score: number | null
  verdict: string | null
  findingsRaw: string | null
}

function DimensionCard({ title, score, verdict, findingsRaw }: DimensionCardProps) {
  const findings = parseTextList(findingsRaw)
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
          format={(value) => (
            <span style={{ color: hasScore ? color : '#999' }}>
              {hasScore ? value : '-'}
            </span>
          )}
        />
        {verdict && (
          <div style={{ marginTop: 8 }}>
            <Text strong style={{ color, fontSize: 13 }}>{verdict}</Text>
          </div>
        )}
      </div>
      {findings.length > 0 && (
        <ul style={{ paddingLeft: 16, margin: 0 }}>
          {findings.map((finding, index) => (
            <li key={`${finding}-${index}`} style={{ marginBottom: 4 }}>
              {finding.includes('异常') || finding.includes('造假') || finding.includes('伪造') || finding.includes('风险') ? (
                <Tag color="red" style={{ marginRight: 4 }}>警告</Tag>
              ) : null}
              <Text>{finding}</Text>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

interface PaperAnalysisResultViewProps {
  result: PaperAnalysisResult
  compact?: boolean
}

export default function PaperAnalysisResultView({ result, compact = false }: PaperAnalysisResultViewProps) {
  const hasOverallScore = result.overall_risk_score !== null && result.overall_risk_score !== undefined
  const overallScore = result.overall_risk_score ?? 0
  const overallColor = getRiskColor(overallScore)
  const riskBadge = getRiskLevelLabel(result.risk_level)
  const recommendations = parseTextList(result.recommendations)

  return (
    <div style={{ marginTop: compact ? 0 : 24 }}>
      {!compact && <Title level={5} style={{ marginBottom: 16 }}>分析结果</Title>}

      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <Card title="综合风险评估">
            <Row gutter={24} align="middle">
              <Col xs={24} sm={8} style={{ textAlign: 'center' }}>
                <Progress
                  type="circle"
                  percent={overallScore}
                  strokeColor={hasOverallScore ? overallColor : '#d9d9d9'}
                  format={(value) => (
                    <span style={{ color: hasOverallScore ? overallColor : '#999' }}>
                      {hasOverallScore ? value : '-'}
                    </span>
                  )}
                  size={120}
                />
                <div style={{ marginTop: 8 }}>
                  <Text>风险等级：</Text>
                  <Tag color={riskBadge.color === 'default' ? '#820014' : riskBadge.color} style={riskBadge.color === 'default' ? { color: '#fff', borderColor: '#820014' } : {}}>
                    {riskBadge.label}
                  </Tag>
                  <Tag>{result.status}</Tag>
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
                      {recommendations.map((recommendation, index) => (
                        <li key={`${recommendation}-${index}`}>{recommendation}</li>
                      ))}
                    </ol>
                  </div>
                )}
              </Col>
            </Row>
          </Card>
        </Col>

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
      </Row>
    </div>
  )
}
