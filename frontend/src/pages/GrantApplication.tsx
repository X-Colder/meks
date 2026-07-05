import { useEffect, useMemo, useState } from 'react'
import { Alert, Button, Card, Checkbox, Col, Form, Input, List, Row, Select, Space, Spin, Tabs, Tag, Typography, message } from 'antd'
import { DatabaseOutlined, FileProtectOutlined, ExperimentOutlined, FileSearchOutlined, FileTextOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import { generateAIResponse } from '@/api/aiAssistant'
import { clinicalDatasetsApi, ClinicalDataset, ClinicalLongitudinalView } from '@/api/clinicalDatasets'
import { documentsApi, DocumentItem } from '@/api/documents'
import { knowledgeBasesApi, KnowledgeBase } from '@/api/knowledgeBases'
import '@/styles/chat-markdown.css'

const { Title, Text } = Typography

const materialOptions = [
  { value: 'full', label: '完整课题申报包' },
  { value: 'proposal', label: '课题申请书' },
  { value: 'ethics', label: '伦理申请材料' },
  { value: 'crf', label: '病例报告表 CRF' },
  { value: 'sap', label: '统计分析计划 SAP' },
  { value: 'consent', label: '知情同意书' },
]

interface GrantFormValues {
  title: string
  clinical_question?: string
  background?: string
  resources?: string
  study_type?: string
  objective?: string
  population?: string
  exposure?: string
  outcome?: string
  material_type?: string
  compliance?: string
  evidence_notes?: string
}

type GrantFieldName = keyof GrantFormValues

const fieldLabels: Partial<Record<GrantFieldName, string>> = {
  clinical_question: '临床问题',
  background: '研究背景',
  resources: '数据资源',
  objective: '研究目标',
  population: '研究对象',
  exposure: '暴露因素',
  outcome: '结局变量',
  compliance: '伦理与数据安全',
  evidence_notes: '医生补充说明',
}

const demoValues: GrantFormValues = {
  title: '高血压合并多疾病患者心血管事件风险预测模型构建研究',
  clinical_question: '在高血压患者中，糖尿病、冠心病、心衰、房颤等共病及 LDL-C、NT-proBNP 等指标能否预测再入院或心血管不良事件？',
  background: '临床中同一患者常跨科室反复就诊，单次就诊记录难以解释疾病进展。以患者主索引整合诊断、检验、用药、手术和随访事件，有助于识别共病组合与结局风险。',
  resources: '已整理患者级纵向病例数据，包含患者 ID、就诊日期、就诊类型、年龄、性别、诊断、ICD-10、检验、用药、操作和结局字段。可结合前沿发现中的心血管风险预测、共病管理和真实世界研究论文作为依据。',
  study_type: 'retrospective cohort',
  objective: '构建面向高血压及相关共病患者的再入院/心血管事件风险预测模型，并形成可解释的风险因素列表。',
  population: '纳入 2021-2025 年在本院有高血压诊断且至少一次随访记录的成年患者；排除关键基线信息缺失严重者。',
  exposure: '糖尿病、冠心病、心衰、房颤、LDL-C 升高、NT-proBNP 升高、既往脑梗死、他汀/抗凝/降压药使用情况',
  outcome: '再入院、心血管不良事件、疾病复发或随访中记录的不良结局',
  material_type: 'full',
  compliance: '使用脱敏 research_patient_id；不导出姓名、身份证、电话、住址；研究团队分级授权访问；保留数据使用审计记录；伦理申请中说明回顾性研究和知情同意豁免依据。',
}

export default function GrantApplication() {
  const [form] = Form.useForm<GrantFormValues>()
  const [loading, setLoading] = useState(false)
  const [sourceLoading, setSourceLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('evidence')
  const [result, setResult] = useState('')
  const [formVersion, setFormVersion] = useState(0)
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [datasets, setDatasets] = useState<ClinicalDataset[]>([])
  const [selectedKbId, setSelectedKbId] = useState<string>()
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([])
  const [selectedDatasetIds, setSelectedDatasetIds] = useState<string[]>([])
  const [datasetViews, setDatasetViews] = useState<Record<string, ClinicalLongitudinalView>>({})
  const [activeField, setActiveField] = useState<GrantFieldName>('clinical_question')
  const [fieldAnchors, setFieldAnchors] = useState<Partial<Record<GrantFieldName, string[]>>>({})

  useEffect(() => {
    setSourceLoading(true)
    Promise.all([
      knowledgeBasesApi.list().then((res) => setKbs(res.data)).catch(() => undefined),
      clinicalDatasetsApi.list().then((res) => setDatasets(res.data)).catch(() => undefined),
    ]).finally(() => setSourceLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedKbId) {
      setDocuments([])
      setSelectedDocIds([])
      return
    }
    documentsApi.list({ knowledge_base_id: selectedKbId, page: 1, page_size: 20 })
      .then((res) => setDocuments(res.data.items))
      .catch(() => message.error('获取知识库论文失败'))
  }, [selectedKbId])

  useEffect(() => {
    selectedDatasetIds.forEach((id) => {
      if (datasetViews[id]) return
      clinicalDatasetsApi.longitudinal(id)
        .then((res) => setDatasetViews((prev) => ({ ...prev, [id]: res.data })))
        .catch(() => undefined)
    })
  }, [selectedDatasetIds, datasetViews])

  const evidenceSummary = useMemo(() => {
    const selectedDocs = documents.filter((doc) => selectedDocIds.includes(doc.id))
    const selectedDatasets = datasets.filter((dataset) => selectedDatasetIds.includes(dataset.id))
    const docText = selectedDocs.map((doc, index) => [
      `论文 ${index + 1}：${doc.title}`,
      `期刊/作者：${doc.journal || '未知'} / ${doc.authors || '未知'}`,
      `发表时间：${doc.publication_date || '未知'}`,
      `鉴真风险：${doc.analysis_risk_score ?? '未完成'}`,
      `摘要：${doc.abstract || '暂无摘要'}`,
    ].join('\n')).join('\n\n')
    const datasetText = selectedDatasets.map((dataset, index) => {
      const view = datasetViews[dataset.id]
      return [
        `病例数据集 ${index + 1}：${dataset.name}`,
        `规模：${dataset.row_count} 行，${dataset.column_count} 列`,
        view ? `患者数：${view.patient_count}，临床事件：${view.event_count}` : '纵向视图：生成中或暂无',
        view ? `字段映射：患者ID=${view.patient_id_column || '未识别'}；时间=${view.date_column || '未识别'}；诊断=${view.diagnosis_columns.join('/') || '未识别'}` : '',
        view ? `主要疾病/共病线索：${view.top_diagnoses.slice(0, 8).map((item) => `${item.diagnosis}(${item.count})`).join('，')}` : '',
      ].filter(Boolean).join('\n')
    }).join('\n\n')
    return [docText, datasetText].filter(Boolean).join('\n\n')
  }, [documents, selectedDocIds, datasets, selectedDatasetIds, datasetViews])

  const selectedDocs = useMemo(() => documents.filter((doc) => selectedDocIds.includes(doc.id)), [documents, selectedDocIds])
  const selectedDatasets = useMemo(() => datasets.filter((dataset) => selectedDatasetIds.includes(dataset.id)), [datasets, selectedDatasetIds])
  const selectedViews = useMemo(() => selectedDatasetIds.map((id) => datasetViews[id]).filter(Boolean), [selectedDatasetIds, datasetViews])

  const datasetFactText = useMemo(() => {
    if (!selectedDatasets.length) return ''
    return selectedDatasets.map((dataset) => {
      const view = datasetViews[dataset.id]
      if (!view) return `${dataset.name}：${dataset.row_count} 行，${dataset.column_count} 列。`
      const diagnoses = view.top_diagnoses.slice(0, 8).map((item) => `${item.diagnosis}(${item.count})`).join('、')
      return `${dataset.name}：患者 ${view.patient_count} 例，临床事件 ${view.event_count} 条；主要疾病/共病包括 ${diagnoses || '待识别'}。`
    }).join('\n')
  }, [selectedDatasets, datasetViews])

  const literatureFactText = useMemo(() => {
    if (!selectedDocs.length) return ''
    return selectedDocs.map((doc, index) => `${index + 1}. ${doc.title}${doc.journal ? `（${doc.journal}）` : ''}：${doc.abstract || '暂无摘要'}${doc.analysis_risk_score !== null && doc.analysis_risk_score !== undefined ? ` 鉴真风险 ${doc.analysis_risk_score}。` : ''}`).join('\n')
  }, [selectedDocs])

  const setField = (name: GrantFieldName, value: string, append = false) => {
    const current = form.getFieldValue(name)
    form.setFieldValue(name, append && current ? `${current}\n${value}` : value)
    setActiveField(name)
  }

  const addAnchors = (name: GrantFieldName, anchors: string[]) => {
    setActiveField(name)
    setFieldAnchors((prev) => {
      const next = new Set([...(prev[name] || []), ...anchors.filter(Boolean)])
      return { ...prev, [name]: Array.from(next).slice(0, 8) }
    })
  }

  const applyFieldSuggestion = (name: GrantFieldName) => {
    const primaryView = selectedViews[0]
    const topDiagnoses = primaryView?.top_diagnoses.slice(0, 6).map((item) => item.diagnosis).join('、') || '高血压、冠心病、心衰、房颤等共病'
    const patientScale = primaryView ? `患者 ${primaryView.patient_count} 例，临床事件 ${primaryView.event_count} 条` : '已有患者级纵向病例数据'
    const currentDocs = selectedDocs.slice(0, 3).map((doc) => doc.title).join('；')
    const docAnchor = currentDocs ? `结合已选文献：${currentDocs}` : '结合前沿文献和临床观察'
    const suggestions: Partial<Record<GrantFieldName, string>> = {
      clinical_question: `在${topDiagnoses}患者中，纵向诊断、检验、用药和随访事件能否用于识别再入院或心血管不良事件风险？`,
      background: `基于病例数据发现：${datasetFactText || patientScale}。这些患者存在多次跨科室就诊和多疾病共病，单次就诊记录难以解释疾病进展和结局风险。\n${docAnchor}，本研究拟整合患者级纵向病例数据，分析共病组合、关键检验指标和治疗事件与临床结局之间的关系。`,
      resources: `${datasetFactText || patientScale}。数据字段包括患者 ID、就诊日期、就诊类型、年龄、性别、诊断、ICD-10、检验、用药、操作和结局。${literatureFactText ? `\n已选文献依据：\n${literatureFactText}` : ''}`,
      objective: '构建基于患者级纵向临床数据的风险识别框架，筛选与再入院或心血管不良事件相关的共病、检验指标和治疗因素，并形成可解释的预测模型。',
      population: primaryView ? `纳入所选病例数据集中可按 ${primaryView.patient_id_column || '患者 ID'} 识别、且存在 ${primaryView.date_column || '就诊时间'} 和诊断记录的成年患者；按目标疾病诊断和随访完整性进一步筛选。` : '纳入本院具有目标疾病诊断且至少一次随访记录的成年患者；排除关键基线信息缺失严重或无法建立患者主索引者。',
      exposure: primaryView ? `候选暴露因素包括主要共病（${topDiagnoses}）、关键检验异常、既往用药、手术/操作和跨科室就诊频次。` : '候选暴露因素包括共病、关键检验异常、既往用药、手术/操作和跨科室就诊频次。',
      outcome: '主要结局可定义为再入院、复发、死亡、心血管不良事件或随访中记录的不良结局；次要结局可包括住院天数、治疗升级、并发症或指标恶化。',
      evidence_notes: '字段锚点：临床问题和研究背景来自病例共病线索与已选论文；研究对象、暴露和结局来自患者级纵向病例数据字段。',
    }
    setField(name, suggestions[name] || '')
    const anchors = [
      datasetFactText ? `病例事实：${datasetFactText}` : primaryView ? `病例事实：患者 ${primaryView.patient_count} 例，事件 ${primaryView.event_count} 条` : '',
      currentDocs ? `文献依据：${currentDocs}` : '',
      primaryView?.patient_id_column ? `患者主索引：${primaryView.patient_id_column}` : '',
      primaryView?.date_column ? `时间字段：${primaryView.date_column}` : '',
      primaryView?.diagnosis_columns.length ? `诊断字段：${primaryView.diagnosis_columns.join('/')}` : '',
    ]
    addAnchors(name, anchors)
  }

  const appendDocAnchor = (name: GrantFieldName) => {
    if (!selectedDocs.length) {
      setField(name, '请先选择文献知识库和论文。', true)
      return
    }
    const text = literatureFactText
    setField(name, text, true)
    addAnchors(name, selectedDocs.slice(0, 3).map((doc) => `文献：${doc.title}${doc.analysis_risk_score !== null && doc.analysis_risk_score !== undefined ? `；鉴真风险 ${doc.analysis_risk_score}` : ''}`))
  }

  const fieldAnchorText = Object.entries(fieldAnchors)
    .map(([field, anchors]) => `${fieldLabels[field as GrantFieldName] || field}：\n${(anchors || []).map((anchor) => `- ${anchor}`).join('\n')}`)
    .join('\n\n')
  const currentValues = useMemo(() => form.getFieldsValue(), [form, formVersion])
  const requiredFields: GrantFieldName[] = ['title', 'clinical_question', 'background', 'population', 'exposure', 'outcome', 'compliance']
  const missingFields = requiredFields.filter((field) => !String(currentValues[field] || '').trim())
  const anchoredFields = (Object.keys(fieldLabels) as GrantFieldName[]).filter((field) => (fieldAnchors[field]?.length || 0) > 0)
  const complianceWarnings = [
    !String(currentValues.compliance || '').includes('脱敏') ? '伦理与数据安全中尚未明确脱敏要求。' : '',
    !String(currentValues.population || '').trim() ? '研究对象/数据来源尚未明确，伦理材料会缺少数据来源说明。' : '',
    !String(currentValues.outcome || '').trim() ? '结局变量尚未明确，统计分析计划无法稳定生成。' : '',
    anchoredFields.length < 4 ? '字段级证据锚点偏少，建议至少为临床问题、背景、研究对象、暴露/结局绑定依据。' : '',
  ].filter(Boolean)

  const generate = async (values: GrantFormValues, target: string) => {
    setLoading(true)
    setResult('')
    setActiveTab(target)
    try {
      const material = materialOptions.find((item) => item.value === values.material_type)?.label || '完整课题申报包'
      const prompt = `你是一位医院科研方法学顾问、课题申报顾问和伦理材料写作顾问。请基于以下信息，生成适合医生继续编辑的课题申报内容。

项目名称：${values.title}
临床问题：${values.clinical_question || '未说明'}
研究背景/前期依据：${values.background || '未说明'}
现有病例/文献/数据资源：${values.resources || '未说明'}
倾向研究类型：${values.study_type || '未指定'}
研究目标：${values.objective || '未说明'}
研究对象/数据来源：${values.population || '未说明'}
暴露变量/干预因素：${values.exposure || '未指定'}
结局变量：${values.outcome || '未指定'}
合规与数据安全要求：${values.compliance || '需使用脱敏数据，遵守医院伦理与数据安全要求'}
材料类型：${material}
医生补充说明：${values.evidence_notes || '未说明'}

字段级证据锚点：
${fieldAnchorText || '暂无字段级证据锚点。'}

已选择的文献/病例依据：
${evidenceSummary || '未选择系统内依据材料。请基于用户输入给出结构化草案，并标明需要补充的文献和病例数据。'}

请按以下结构输出，缺失信息请明确标注“需医生补充”，不要编造伦理批号、基金编号或不存在的数据：

## 一、研究设计
1. 研究题目建议
2. PICO/PECO 框架
3. 研究假设
4. 研究类型与总体设计
5. 纳入标准与排除标准
6. 暴露变量、结局变量和协变量
7. 样本量与统计分析建议
8. 潜在偏倚与控制方法

## 二、课题申请书正文
1. 立项依据
2. 研究目的
3. 研究内容
4. 技术路线
5. 创新点
6. 可行性分析
7. 预期成果

## 三、伦理与数据安全
1. 研究对象权益保护
2. 知情同意或豁免知情同意理由
3. 隐私保护与数据脱敏
4. 数据访问权限与审计
5. 风险收益评估

## 四、研究执行材料
1. CRF 字段草案
2. 数据字典草案
3. 统计分析计划 SAP
4. 进度安排`
      setResult(await generateAIResponse(prompt))
    } catch {
      message.error('生成课题申报内容失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Title level={4}><FileProtectOutlined /> 课题申报</Title>
      <Text type="secondary">把临床问题、文献依据和病例数据资源整理成研究设计、申请书、伦理材料、CRF 和统计分析计划。</Text>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} lg={9}>
          <Card size="small" title="申报基础信息">
            <Alert
              type="info"
              showIcon
              message="业务逻辑"
              description="先选择文献、精读/鉴真结果和病例数据作为依据，再让 AI 生成研究设计、申请书正文、伦理材料和执行材料；文本框只用于补充医生自己的临床判断。"
              style={{ marginBottom: 12 }}
            />
            <Form
              form={form}
              layout="vertical"
              onFinish={(values) => generate(values, 'materials')}
              onValuesChange={() => setFormVersion((value) => value + 1)}
              initialValues={{ material_type: 'full', compliance: '使用脱敏病例数据，限定研究团队访问，保留数据使用审计记录。' }}
            >
              <Button
                block
                style={{ marginBottom: 12 }}
                icon={<FileSearchOutlined />}
                onClick={() => {
                  form.setFieldsValue(demoValues)
                  const demoDataset = datasets.find((item) => item.name.includes('模拟纵向病例数据')) || datasets[0]
                  if (demoDataset) setSelectedDatasetIds([demoDataset.id])
                  setActiveField('clinical_question')
                  setFieldAnchors({
                    clinical_question: ['病例线索：高血压、冠心病、心衰、房颤等共病患者存在多次就诊和随访事件'],
                    background: ['临床事实：患者级纵向数据可反映疾病进展、跨科室就诊和结局事件'],
                    resources: ['数据来源：模拟纵向病例数据_患者主索引'],
                  })
                  message.success('已填入测试申报数据')
                }}
              >
                填入测试数据
              </Button>
              <Form.Item name="title" label="项目名称" rules={[{ required: true }]}>
                <Input placeholder="例如：炎症指标预测房颤消融术后复发的回顾性队列研究" />
              </Form.Item>
              <Form.Item name="clinical_question" label="临床问题" rules={[{ required: true }]}>
                <Input.TextArea rows={3} placeholder="例如：房颤消融患者术后复发是否与术前炎症指标相关？" onFocus={() => setActiveField('clinical_question')} />
              </Form.Item>
              <FieldTools items={[
                ['从病例共病线索生成', () => applyFieldSuggestion('clinical_question')],
                ['追加文献启发', () => {
                  if (selectedDocs[0]) {
                    setField('clinical_question', `基于文献“${selectedDocs[0].title}”提示的研究方向，进一步验证其在本院真实世界患者中的适用性。`, true)
                    addAnchors('clinical_question', [`文献启发：${selectedDocs[0].title}`])
                  } else {
                    setField('clinical_question', '请先选择论文。', true)
                  }
                }],
              ]} />
              <FieldAnchorTags anchors={fieldAnchors.clinical_question} />
              <Form.Item name="background" label="研究背景/前期依据">
                <Input.TextArea rows={3} placeholder="可填写前沿发现、文献精读或临床观察得到的依据。" onFocus={() => setActiveField('background')} />
              </Form.Item>
              <FieldTools items={[
                ['融入病例事实', () => applyFieldSuggestion('background')],
                ['融入已选论文', () => appendDocAnchor('background')],
              ]} />
              <FieldAnchorTags anchors={fieldAnchors.background} />
              <Form.Item name="resources" label="现有病例/文献/数据资源">
                <Input.TextArea rows={3} placeholder="例如：我科 2020-2025 年房颤消融患者约 300 例，包含血常规、超声和随访复发情况。" onFocus={() => setActiveField('resources')} />
              </Form.Item>
              <FieldTools items={[
                ['从病例数据集导入', () => applyFieldSuggestion('resources')],
                ['追加论文依据', () => appendDocAnchor('resources')],
              ]} />
              <FieldAnchorTags anchors={fieldAnchors.resources} />
              <Row gutter={12}>
                <Col span={12}>
                  <Form.Item name="study_type" label="研究类型">
                    <Select allowClear options={[
                      { value: 'retrospective cohort', label: '回顾性队列' },
                      { value: 'case-control', label: '病例对照' },
                      { value: 'cross-sectional', label: '横断面研究' },
                      { value: 'prospective cohort', label: '前瞻性队列' },
                      { value: 'randomized trial', label: '随机对照研究' },
                    ]} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="material_type" label="输出材料">
                    <Select options={materialOptions} />
                  </Form.Item>
                </Col>
              </Row>
              <Form.Item name="objective" label="研究目标">
                <Input placeholder="例如：筛选复发风险因素并构建风险预测模型" onFocus={() => setActiveField('objective')} />
              </Form.Item>
              <FieldTools items={[['从临床问题生成目标', () => applyFieldSuggestion('objective')]]} />
              <FieldAnchorTags anchors={fieldAnchors.objective} />
              <Row gutter={12}>
                <Col span={12}>
                  <Form.Item name="exposure" label="暴露/干预因素">
                    <Input placeholder="例如：NLR、CRP、LDL-C" onFocus={() => setActiveField('exposure')} />
                  </Form.Item>
                  <FieldTools compact items={[['从字段/共病导入', () => applyFieldSuggestion('exposure')]]} />
                  <FieldAnchorTags anchors={fieldAnchors.exposure} compact />
                </Col>
                <Col span={12}>
                  <Form.Item name="outcome" label="结局变量">
                    <Input placeholder="例如：术后 12 个月复发" onFocus={() => setActiveField('outcome')} />
                  </Form.Item>
                  <FieldTools compact items={[['从结局事件导入', () => applyFieldSuggestion('outcome')]]} />
                  <FieldAnchorTags anchors={fieldAnchors.outcome} compact />
                </Col>
              </Row>
              <Form.Item name="population" label="研究对象/数据来源">
                <Input.TextArea rows={2} placeholder="例如：某院心内科接受导管消融治疗的房颤患者。" onFocus={() => setActiveField('population')} />
              </Form.Item>
              <FieldTools items={[['从患者主索引生成', () => applyFieldSuggestion('population')]]} />
              <FieldAnchorTags anchors={fieldAnchors.population} />
              <Form.Item name="compliance" label="伦理与数据安全要求">
                <Input.TextArea rows={2} />
              </Form.Item>
              <Form.Item name="evidence_notes" label="医生补充说明">
                <Input.TextArea rows={2} placeholder="例如：希望重点突出真实世界研究价值、患者纵向数据整合和共病风险识别。" />
              </Form.Item>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button type="primary" htmlType="submit" loading={loading} block icon={<FileProtectOutlined />}>生成完整申报内容</Button>
                <Button block icon={<ExperimentOutlined />} onClick={() => form.validateFields().then((values) => generate(values, 'design'))}>只生成研究设计</Button>
                <Button block icon={<SafetyCertificateOutlined />} onClick={() => form.validateFields().then((values) => generate(values, 'compliance'))}>只生成伦理与数据安全</Button>
              </Space>
            </Form>
          </Card>
          <Card size="small" title="依据材料" style={{ marginTop: 16 }} loading={sourceLoading}>
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Alert
                type="info"
                showIcon
                message="字段级数据锚点"
                description="选择资料后，在上方各字段下点击导入按钮，把病例事实、文献依据、变量和结局分别写入对应申报字段。"
              />
              <div>
                <Text strong><FileTextOutlined /> 文献知识库</Text>
                <Select
                  allowClear
                  placeholder="选择知识库后加载论文"
                  value={selectedKbId}
                  onChange={setSelectedKbId}
                  style={{ width: '100%', marginTop: 8 }}
                  options={kbs.map((kb) => ({ value: kb.id, label: `${kb.name} (${kb.document_count})` }))}
                />
              </div>
              {documents.length > 0 && (
                <Checkbox.Group value={selectedDocIds} onChange={(values) => setSelectedDocIds(values as string[])} style={{ width: '100%' }}>
                  <List
                    size="small"
                    dataSource={documents.slice(0, 6)}
                    renderItem={(doc) => (
                      <List.Item>
                        <Checkbox value={doc.id}>
                          <Space direction="vertical" size={2}>
                            <Text ellipsis style={{ maxWidth: 280 }}>{doc.title}</Text>
                            <Space size={4} wrap>
                              <Tag>{doc.status}</Tag>
                              {doc.analysis_risk_score !== null && doc.analysis_risk_score !== undefined && <Tag color={doc.analysis_risk_score < 30 ? 'green' : 'orange'}>风险 {doc.analysis_risk_score}</Tag>}
                            </Space>
                          </Space>
                        </Checkbox>
                      </List.Item>
                    )}
                  />
                </Checkbox.Group>
              )}
              <div>
                <Text strong><DatabaseOutlined /> 病例数据集</Text>
                <Select
                  mode="multiple"
                  placeholder="选择病例数据集作为申报依据"
                  value={selectedDatasetIds}
                  onChange={setSelectedDatasetIds}
                  style={{ width: '100%', marginTop: 8 }}
                  options={datasets.map((dataset) => ({ value: dataset.id, label: `${dataset.name} (${dataset.row_count}行)` }))}
                />
              </div>
              {evidenceSummary && (
                <Card size="small" title="已汇总依据" style={{ background: '#fafafa' }}>
                  <pre style={{ whiteSpace: 'pre-wrap', margin: 0, maxHeight: 220, overflow: 'auto' }}>{evidenceSummary}</pre>
                </Card>
              )}
            </Space>
          </Card>
        </Col>

        <Col xs={24} lg={15}>
          <Card size="small" title="申报字段证据矩阵" style={{ marginBottom: 16 }}>
            <Row gutter={[8, 8]}>
              {(Object.keys(fieldLabels) as GrantFieldName[]).map((field) => (
                <Col xs={24} md={12} key={field}>
                  <Card
                    size="small"
                    hoverable
                    onClick={() => setActiveField(field)}
                    style={{ borderColor: activeField === field ? '#1677ff' : undefined }}
                  >
                    <Space direction="vertical" size={4} style={{ width: '100%' }}>
                      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                        <Text strong>{fieldLabels[field]}</Text>
                        <Tag color={(fieldAnchors[field]?.length || 0) > 0 ? 'green' : 'default'}>{fieldAnchors[field]?.length || 0} 个锚点</Tag>
                      </Space>
                      {(fieldAnchors[field] || []).slice(0, 2).map((anchor) => (
                        <Text key={anchor} type="secondary" ellipsis>{anchor}</Text>
                      ))}
                      {!(fieldAnchors[field]?.length) && <Text type="secondary">等待从病例/论文导入</Text>}
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
          <Card size="small" title="课题申报工作区">
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              items={[
                {
                  key: 'evidence',
                  label: '选题依据',
                  children: (
                    <EvidenceWorkspace
                      datasetFactText={datasetFactText}
                      literatureFactText={literatureFactText}
                      selectedDocs={selectedDocs}
                      selectedDatasets={selectedDatasets}
                      fieldAnchors={fieldAnchors}
                      onSeedFields={() => {
                        ;(['clinical_question', 'background', 'resources', 'population', 'exposure', 'outcome'] as GrantFieldName[]).forEach(applyFieldSuggestion)
                        message.success('已将证据池写入核心申报字段')
                      }}
                    />
                  ),
                },
                { key: 'design', label: '研究设计', children: <Section result={result} loading={loading} empty="业务用途：把临床问题、文献依据和病例数据转成可执行研究方案，包括 PICO、研究类型、纳排标准、变量、终点、样本量和统计方法。" /> },
                { key: 'compliance', label: '伦理合规', children: <ComplianceWorkspace result={result} loading={loading} warnings={complianceWarnings} /> },
                { key: 'materials', label: '申报材料', children: <Section result={result} loading={loading} empty="业务用途：把研究设计展开成课题申请书正文、技术路线、创新点、CRF、数据字典、SAP 和进度安排。" /> },
                { key: 'review', label: '提交前检查', children: <ReviewWorkspace missingFields={missingFields} anchoredFields={anchoredFields} complianceWarnings={complianceWarnings} fieldAnchors={fieldAnchors} /> },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

function Section({ result, loading, empty }: { result: string; loading: boolean; empty: string }) {
  return (
    <Spin spinning={loading}>
      <div className="chat-markdown" style={{ minHeight: 520 }}>
        {result ? <ReactMarkdown>{result}</ReactMarkdown> : (
          <Space direction="vertical" size={12}>
            <Text type="secondary">{empty}</Text>
            <Text type="secondary"><FileTextOutlined /> 建议先从前沿发现、文献精读或病例数据集中复制关键依据，再生成申报内容。</Text>
          </Space>
        )}
      </div>
    </Spin>
  )
}

function EvidenceWorkspace({
  datasetFactText,
  literatureFactText,
  selectedDocs,
  selectedDatasets,
  fieldAnchors,
  onSeedFields,
}: {
  datasetFactText: string
  literatureFactText: string
  selectedDocs: DocumentItem[]
  selectedDatasets: ClinicalDataset[]
  fieldAnchors: Partial<Record<GrantFieldName, string[]>>
  onSeedFields: () => void
}) {
  const anchorCount = Object.values(fieldAnchors).reduce((sum, anchors) => sum + (anchors?.length || 0), 0)
  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        message="选题依据的作用"
        description="这里不是材料附件，而是把病例事实、论文依据和医生观察拆成可写入申报字段的数据锚点。"
      />
      <Row gutter={12}>
        <Col xs={24} md={8}><MetricCard label="已选文献" value={selectedDocs.length} /></Col>
        <Col xs={24} md={8}><MetricCard label="病例数据集" value={selectedDatasets.length} /></Col>
        <Col xs={24} md={8}><MetricCard label="字段锚点" value={anchorCount} /></Col>
      </Row>
      <Card size="small" title="病例事实">
        {datasetFactText ? <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{datasetFactText}</pre> : <Text type="secondary">请选择病例数据集，系统会汇总患者数、临床事件、主要疾病和共病线索。</Text>}
      </Card>
      <Card size="small" title="文献依据">
        {literatureFactText ? <pre style={{ whiteSpace: 'pre-wrap', margin: 0, maxHeight: 180, overflow: 'auto' }}>{literatureFactText}</pre> : <Text type="secondary">请选择文献知识库和论文，系统会将摘要、期刊、鉴真风险写入依据池。</Text>}
      </Card>
      <Button type="primary" icon={<FileSearchOutlined />} onClick={onSeedFields}>
        将证据池写入核心字段
      </Button>
    </Space>
  )
}

function ComplianceWorkspace({ result, loading, warnings }: { result: string; loading: boolean; warnings: string[] }) {
  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {warnings.length > 0 ? (
        warnings.map((warning) => <Alert key={warning} type="warning" showIcon message={warning} />)
      ) : (
        <Alert type="success" showIcon message="当前基础合规要素较完整" description="仍需由医生和伦理办公室确认具体研究类型、知情同意要求和数据安全规范。" />
      )}
      <Section result={result} loading={loading} empty="业务用途：把病例数据使用方式整理成伦理申请材料，包括知情同意/豁免理由、隐私保护、脱敏策略、访问控制和风险收益评估。" />
    </Space>
  )
}

function ReviewWorkspace({
  missingFields,
  anchoredFields,
  complianceWarnings,
  fieldAnchors,
}: {
  missingFields: GrantFieldName[]
  anchoredFields: GrantFieldName[]
  complianceWarnings: string[]
  fieldAnchors: Partial<Record<GrantFieldName, string[]>>
}) {
  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Row gutter={12}>
        <Col xs={24} md={8}><MetricCard label="缺失字段" value={missingFields.length} tone={missingFields.length ? 'warning' : 'success'} /></Col>
        <Col xs={24} md={8}><MetricCard label="已锚定字段" value={anchoredFields.length} tone={anchoredFields.length >= 4 ? 'success' : 'warning'} /></Col>
        <Col xs={24} md={8}><MetricCard label="合规提醒" value={complianceWarnings.length} tone={complianceWarnings.length ? 'warning' : 'success'} /></Col>
      </Row>
      <Card size="small" title="材料完整性">
        {missingFields.length ? (
          <Space wrap>
            {missingFields.map((field) => <Tag key={field} color="orange">{fieldLabels[field]}</Tag>)}
          </Space>
        ) : (
          <Text type="success">核心申报字段已填写。</Text>
        )}
      </Card>
      <Card size="small" title="证据锚点检查">
        <Space direction="vertical" style={{ width: '100%' }}>
          {(Object.keys(fieldLabels) as GrantFieldName[]).map((field) => (
            <div key={field} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
              <Text>{fieldLabels[field]}</Text>
              <Tag color={(fieldAnchors[field]?.length || 0) > 0 ? 'green' : 'default'}>{fieldAnchors[field]?.length || 0} 个锚点</Tag>
            </div>
          ))}
        </Space>
      </Card>
      <Card size="small" title="合规风险">
        {complianceWarnings.length ? (
          <Space direction="vertical">
            {complianceWarnings.map((warning) => <Text key={warning} type="warning">{warning}</Text>)}
          </Space>
        ) : (
          <Text type="success">暂无基础合规风险提醒。</Text>
        )}
      </Card>
    </Space>
  )
}

function MetricCard({ label, value, tone = 'default' }: { label: string; value: number; tone?: 'default' | 'success' | 'warning' }) {
  const color = tone === 'success' ? '#52c41a' : tone === 'warning' ? '#faad14' : '#1677ff'
  return (
    <Card size="small">
      <Text type="secondary">{label}</Text>
      <div style={{ color, fontSize: 28, fontWeight: 700, lineHeight: '36px' }}>{value}</div>
    </Card>
  )
}

function FieldTools({ items, compact = false }: { items: [string, () => void][]; compact?: boolean }) {
  return (
    <Space wrap size={6} style={{ marginTop: compact ? -12 : -16, marginBottom: 12 }}>
      {items.map(([label, onClick]) => (
        <Button key={label} size="small" type="dashed" onClick={onClick}>
          {label}
        </Button>
      ))}
    </Space>
  )
}

function FieldAnchorTags({ anchors, compact = false }: { anchors?: string[]; compact?: boolean }) {
  if (!anchors?.length) return null
  return (
    <Space wrap size={4} style={{ marginTop: compact ? -6 : -8, marginBottom: 12 }}>
      {anchors.slice(0, compact ? 2 : 4).map((anchor) => (
        <Tag key={anchor} color="blue">{anchor.length > 28 ? `${anchor.slice(0, 28)}...` : anchor}</Tag>
      ))}
    </Space>
  )
}
