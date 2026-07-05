import { useEffect, useState } from 'react'
import { Alert, Button, Card, Col, Empty, Form, Input, List, Progress, Row, Space, Spin, Table, Tabs, Tag, Timeline, Typography, Upload, message } from 'antd'
import { DatabaseOutlined, InboxOutlined, LineChartOutlined, PartitionOutlined, UserOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import { clinicalDatasetsApi, ClinicalDataset, ClinicalDatasetDetail, ClinicalLongitudinalView, ClinicalPatientSummary, ClinicalStats } from '@/api/clinicalDatasets'
import '@/styles/chat-markdown.css'

const { Title, Text } = Typography
const { Dragger } = Upload

function typeColor(type: string) {
  if (type === 'numeric') return 'blue'
  if (type === 'categorical') return 'green'
  if (type === 'text') return 'orange'
  return 'default'
}

export default function ClinicalDatasets() {
  const [datasets, setDatasets] = useState<ClinicalDataset[]>([])
  const [selected, setSelected] = useState<ClinicalDatasetDetail | null>(null)
  const [stats, setStats] = useState<ClinicalStats | null>(null)
  const [longitudinal, setLongitudinal] = useState<ClinicalLongitudinalView | null>(null)
  const [activePatientId, setActivePatientId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [suggestionLoading, setSuggestionLoading] = useState(false)
  const [suggestion, setSuggestion] = useState('')
  const [form] = Form.useForm()

  const fetchDatasets = async () => {
    const res = await clinicalDatasetsApi.list()
    setDatasets(res.data)
  }

  useEffect(() => { fetchDatasets() }, [])

  const openDataset = async (dataset: ClinicalDataset) => {
    setLoading(true)
    setSuggestion('')
    try {
      const [detail, statRes, longitudinalRes] = await Promise.all([
        clinicalDatasetsApi.get(dataset.id),
        clinicalDatasetsApi.stats(dataset.id),
        clinicalDatasetsApi.longitudinal(dataset.id),
      ])
      setSelected(detail.data)
      setStats(statRes.data)
      setLongitudinal(longitudinalRes.data)
      setActivePatientId(longitudinalRes.data.patients[0]?.patient_id || null)
    } finally {
      setLoading(false)
    }
  }

  const generateSuggestion = async (values: { clinical_question?: string; exposure?: string; outcome?: string }) => {
    if (!selected) return
    setSuggestionLoading(true)
    try {
      const res = await clinicalDatasetsApi.suggestions(selected.id, values)
      setSuggestion(res.data.content)
    } catch {
      message.error('生成科研建议失败')
    } finally {
      setSuggestionLoading(false)
    }
  }

  const previewColumns = selected?.columns.slice(0, 8).map((col) => ({
    title: col.name,
    dataIndex: col.name,
    ellipsis: true,
    width: 130,
  })) || []

  const activePatient = longitudinal?.patients.find((patient) => patient.patient_id === activePatientId) || longitudinal?.patients[0]
  const activeEvents = longitudinal?.events.filter((event) => event.patient_id === activePatient?.patient_id).slice(0, 20) || []
  const patientColumns = [
    { title: '研究患者 ID', dataIndex: 'patient_id', ellipsis: true, width: 150 },
    { title: '性别', dataIndex: 'sex', width: 70, render: (v: string | null) => v || '-' },
    { title: '年龄', dataIndex: 'age', width: 70, render: (v: string | null) => v || '-' },
    { title: '就诊次数', dataIndex: 'encounter_count', width: 90 },
    { title: '诊断数', dataIndex: 'diagnosis_count', width: 80 },
    { title: '时间范围', key: 'range', width: 190, render: (_: unknown, record: ClinicalPatientSummary) => `${record.first_visit || '-'} ~ ${record.last_visit || '-'}` },
    { title: '主要诊断', dataIndex: 'diagnoses', ellipsis: true, render: (items: string[]) => items.slice(0, 3).join('；') || '-' },
  ]
  const cohortColumns = longitudinal?.cohort_preview[0]
    ? Object.keys(longitudinal.cohort_preview[0]).map((key) => ({ title: key, dataIndex: key, ellipsis: true, width: 150 }))
    : []

  return (
    <div>
      <Title level={4}><DatabaseOutlined /> 病例数据集</Title>
      <Text type="secondary">面向医生常见 Excel/CSV 工作方式：上传数据、识别变量、查看缺失率和基础统计，并生成科研选题建议。</Text>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} lg={7}>
          <Card size="small" title="上传数据" style={{ marginBottom: 16 }}>
            <Dragger
              accept=".csv,.xlsx"
              showUploadList={false}
              customRequest={async ({ file, onSuccess, onError }) => {
                setUploading(true)
                try {
                  const res = await clinicalDatasetsApi.upload(file as File)
                  message.success('数据集上传成功')
                  onSuccess?.({})
                  await fetchDatasets()
                  setSelected(res.data)
                  const [statRes, longitudinalRes] = await Promise.all([
                    clinicalDatasetsApi.stats(res.data.id),
                    clinicalDatasetsApi.longitudinal(res.data.id),
                  ])
                  setStats(statRes.data)
                  setLongitudinal(longitudinalRes.data)
                  setActivePatientId(longitudinalRes.data.patients[0]?.patient_id || null)
                } catch (err) {
                  message.error('上传失败，请确认文件为 CSV 或 XLSX')
                  onError?.(err as Error)
                } finally {
                  setUploading(false)
                }
              }}
            >
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">{uploading ? '上传中...' : '上传 CSV / XLSX'}</p>
              <p className="ant-upload-hint">建议先上传脱敏后的科研数据表。</p>
            </Dragger>
          </Card>

          <Card size="small" title="我的数据集">
            <List
              dataSource={datasets}
              locale={{ emptyText: '暂无数据集' }}
              renderItem={(item) => (
                <List.Item onClick={() => openDataset(item)} style={{ cursor: 'pointer' }}>
                  <List.Item.Meta
                    title={<Text strong={selected?.id === item.id}>{item.name}</Text>}
                    description={`${item.row_count} 行 · ${item.column_count} 列 · ${item.created_at.slice(0, 10)}`}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>

        <Col xs={24} lg={17}>
          <Spin spinning={loading}>
            {!selected ? (
              <Card><Empty description="请上传或选择一个病例数据集" /></Card>
            ) : (
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                <Card size="small" title={`${selected.name} 数据资产概览`}>
                  <Row gutter={16}>
                    <Col span={6}><Text strong>原始行数：</Text>{selected.row_count}</Col>
                    <Col span={6}><Text strong>字段数：</Text>{selected.column_count}</Col>
                    <Col span={6}><Text strong>患者数：</Text>{longitudinal?.patient_count ?? '-'}</Col>
                    <Col span={6}><Text strong>临床事件：</Text>{longitudinal?.event_count ?? '-'}</Col>
                  </Row>
                </Card>

                <Tabs
                  items={[
                    {
                      key: 'longitudinal',
                      label: <span><PartitionOutlined /> 患者纵向视图</span>,
                      children: (
                        <Space direction="vertical" size={16} style={{ width: '100%' }}>
                          {longitudinal?.warnings.map((warning) => (
                            <Alert key={warning} type="warning" showIcon message={warning} />
                          ))}
                          <Card size="small" title="AI 字段映射结果">
                            <Space wrap>
                              <Tag color={longitudinal?.patient_id_column ? 'green' : 'orange'}>患者 ID：{longitudinal?.patient_id_column || '未识别'}</Tag>
                              <Tag color={longitudinal?.date_column ? 'green' : 'orange'}>时间字段：{longitudinal?.date_column || '未识别'}</Tag>
                              <Tag color={longitudinal?.diagnosis_columns.length ? 'green' : 'orange'}>诊断字段：{longitudinal?.diagnosis_columns.join(' / ') || '未识别'}</Tag>
                            </Space>
                          </Card>
                          <Row gutter={16}>
                            <Col xs={24} lg={15}>
                              <Card size="small" title="患者主索引">
                                <Table
                                  rowKey="patient_id"
                                  size="small"
                                  dataSource={longitudinal?.patients || []}
                                  columns={patientColumns}
                                  pagination={{ pageSize: 8, showSizeChanger: false }}
                                  onRow={(record) => ({ onClick: () => setActivePatientId(record.patient_id), style: { cursor: 'pointer' } })}
                                  scroll={{ x: true }}
                                />
                              </Card>
                            </Col>
                            <Col xs={24} lg={9}>
                              <Card size="small" title={activePatient ? `患者时间线：${activePatient.patient_id}` : '患者时间线'}>
                                {activeEvents.length === 0 ? (
                                  <Empty description="暂无时间线事件" />
                                ) : (
                                  <Timeline
                                    items={activeEvents.map((event) => ({
                                      children: (
                                        <div>
                                          <Text strong>{event.date || '未知时间'} · {event.event_type}</Text>
                                          <div>{event.title}</div>
                                          <Text type="secondary" style={{ fontSize: 12 }}>{Object.entries(event.details).slice(0, 4).map(([key, value]) => `${key}: ${value}`).join('；')}</Text>
                                        </div>
                                      ),
                                    }))}
                                  />
                                )}
                              </Card>
                            </Col>
                          </Row>
                        </Space>
                      ),
                    },
                    {
                      key: 'cohort',
                      label: <span><UserOutlined /> 队列构建</span>,
                      children: (
                        <Space direction="vertical" size={16} style={{ width: '100%' }}>
                          <Row gutter={16}>
                            <Col xs={24} lg={8}>
                              <Card size="small" title="疾病/共病线索">
                                <List
                                  size="small"
                                  dataSource={longitudinal?.top_diagnoses || []}
                                  locale={{ emptyText: '暂无诊断统计' }}
                                  renderItem={(item) => (
                                    <List.Item>
                                      <Text>{item.diagnosis}</Text>
                                      <Tag color="blue">{item.count}</Tag>
                                    </List.Item>
                                  )}
                                />
                              </Card>
                            </Col>
                            <Col xs={24} lg={16}>
                              <Card size="small" title="AI 队列草案">
                                <Space direction="vertical" size={8}>
                                  <Text><Text strong>患者主索引：</Text>按患者 ID 合并多次就诊，避免把同一患者拆成孤立记录。</Text>
                                  <Text><Text strong>纳入人群：</Text>选择包含目标诊断或关键检验/用药事件的患者。</Text>
                                  <Text><Text strong>暴露变量：</Text>从诊断、检验、用药、手术或生活方式字段中定义。</Text>
                                  <Text><Text strong>结局变量：</Text>从复发、死亡、再入院、手术、并发症等事件中定义。</Text>
                                  <Text><Text strong>协变量：</Text>年龄、性别、共病、基线检验、既往用药等。</Text>
                                  <Alert type="info" showIcon message="下一步可扩展为可配置的纳入排除、时间窗、基线期、随访期和终点事件抽取。" />
                                </Space>
                              </Card>
                            </Col>
                          </Row>
                          <Card size="small" title="研究分析表预览">
                            <Table
                              rowKey={(_, i) => String(i)}
                              size="small"
                              dataSource={longitudinal?.cohort_preview || []}
                              columns={cohortColumns}
                              scroll={{ x: true }}
                              pagination={{ pageSize: 8, showSizeChanger: false }}
                            />
                          </Card>
                        </Space>
                      ),
                    },
                    {
                      key: 'quality',
                      label: '字段质检与基础统计',
                      children: (
                        <Space direction="vertical" size={16} style={{ width: '100%' }}>
                          <Card size="small" title="变量字典与缺失率">
                            <Table
                              rowKey="name"
                              size="small"
                              dataSource={selected.columns}
                              pagination={{ pageSize: 8, showSizeChanger: false }}
                              columns={[
                                { title: '字段', dataIndex: 'name', ellipsis: true },
                                { title: '类型', dataIndex: 'inferred_type', width: 110, render: (v: string) => <Tag color={typeColor(v)}>{v}</Tag> },
                                { title: '角色建议', dataIndex: 'role', width: 110, render: (v: string | null) => v ? <Tag>{v}</Tag> : '-' },
                                { title: '唯一值', dataIndex: 'unique_count', width: 90 },
                                { title: '缺失率', dataIndex: 'missing_rate', width: 150, render: (v: number) => <Progress percent={Math.round(v * 100)} size="small" /> },
                              ]}
                            />
                          </Card>
                          <Card size="small" title="数据预览">
                            <Table
                              rowKey={(_, i) => String(i)}
                              size="small"
                              dataSource={selected.preview_rows}
                              columns={previewColumns}
                              scroll={{ x: true }}
                              pagination={{ pageSize: 8, showSizeChanger: false }}
                            />
                          </Card>
                          {stats && (
                            <Card size="small" title="基础统计">
                              <Row gutter={16}>
                                <Col xs={24} lg={12}>
                                  <Title level={5}>数值变量摘要</Title>
                                  <pre style={{ whiteSpace: 'pre-wrap', background: '#fafafa', padding: 12, borderRadius: 6 }}>{JSON.stringify(stats.numeric_summary, null, 2)}</pre>
                                </Col>
                                <Col xs={24} lg={12}>
                                  <Title level={5}>分类变量摘要</Title>
                                  <pre style={{ whiteSpace: 'pre-wrap', background: '#fafafa', padding: 12, borderRadius: 6 }}>{JSON.stringify(stats.categorical_summary, null, 2)}</pre>
                                </Col>
                              </Row>
                            </Card>
                          )}
                        </Space>
                      ),
                    },
                    {
                      key: 'suggestion',
                      label: '科研建议',
                      children: (
                        <Card size="small" title="科研选题与论文结果段落建议">
                          <Form form={form} layout="vertical" onFinish={generateSuggestion}>
                            <Row gutter={12}>
                              <Col xs={24} lg={10}>
                                <Form.Item name="clinical_question" label="临床问题">
                                  <Input.TextArea rows={3} placeholder="例如：术前炎症指标能否预测房颤消融术后复发？" />
                                </Form.Item>
                              </Col>
                              <Col xs={24} lg={5}>
                                <Form.Item name="exposure" label="暴露变量"><Input placeholder="例如：NLR" /></Form.Item>
                              </Col>
                              <Col xs={24} lg={5}>
                                <Form.Item name="outcome" label="结局变量"><Input placeholder="例如：recurrence" /></Form.Item>
                              </Col>
                              <Col xs={24} lg={4}>
                                <Form.Item label=" "><Button block type="primary" htmlType="submit" loading={suggestionLoading} icon={<LineChartOutlined />}>生成建议</Button></Form.Item>
                              </Col>
                            </Row>
                          </Form>
                          <Spin spinning={suggestionLoading}>
                            {suggestion && <div className="chat-markdown"><ReactMarkdown>{suggestion}</ReactMarkdown></div>}
                          </Spin>
                        </Card>
                      ),
                    },
                  ]}
                />
              </Space>
            )}
          </Spin>
        </Col>
      </Row>
    </div>
  )
}
