import { useState } from 'react'
import { Button, Card, Col, Form, Input, Row, Select, Spin, Typography, message } from 'antd'
import { ExperimentOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import { generateAIResponse } from '@/api/aiAssistant'
import '@/styles/chat-markdown.css'

const { Title, Text } = Typography

export default function ResearchDesign() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState('')

  const handleGenerate = async (values: { question: string; resources?: string; study_type?: string; objective?: string }) => {
    setLoading(true)
    setResult('')
    try {
      const prompt = `请作为医学科研方法学顾问，帮助医生把临床问题转化为可执行研究方案。

临床问题：${values.question}
现有资源/病例数据：${values.resources || '未说明'}
倾向研究类型：${values.study_type || '未指定'}
研究目标：${values.objective || '未说明'}

请输出：
1. 可行研究题目（3个）
2. PICO/PECO 框架
3. 研究假设
4. 研究设计建议
5. 纳入与排除标准
6. 主要终点与次要终点
7. 核心变量表
8. 样本量和统计方法建议
9. 潜在偏倚与控制方法
10. 可写入课题申请书的研究方案摘要`
      setResult(await generateAIResponse(prompt))
    } catch {
      message.error('生成研究设计失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Title level={4}><ExperimentOutlined /> 研究设计</Title>
      <Text type="secondary">把临床问题、病例资源和研究目标转化为 PICO、变量表、终点和统计方案。</Text>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} lg={9}>
          <Card size="small" title="输入研究想法">
            <Form form={form} layout="vertical" onFinish={handleGenerate}>
              <Form.Item name="question" label="临床问题" rules={[{ required: true }]}>
                <Input.TextArea rows={4} placeholder="例如：房颤消融患者术后复发是否与炎症指标相关？" />
              </Form.Item>
              <Form.Item name="resources" label="现有病例/数据资源">
                <Input.TextArea rows={3} placeholder="例如：我科有 300 例房颤消融患者，包含术前血常规、超声、随访复发情况。" />
              </Form.Item>
              <Form.Item name="study_type" label="倾向研究类型">
                <Select allowClear options={[
                  { value: 'retrospective cohort', label: '回顾性队列' },
                  { value: 'case-control', label: '病例对照' },
                  { value: 'cross-sectional', label: '横断面研究' },
                  { value: 'prospective cohort', label: '前瞻性队列' },
                  { value: 'randomized trial', label: '随机对照研究' },
                ]} />
              </Form.Item>
              <Form.Item name="objective" label="研究目标">
                <Input placeholder="例如：寻找复发风险预测因子，构建风险评分" />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>生成研究设计</Button>
            </Form>
          </Card>
        </Col>
        <Col xs={24} lg={15}>
          <Card size="small" title="研究设计建议">
            <Spin spinning={loading}>
              <div className="chat-markdown" style={{ minHeight: 420 }}>
                {result ? <ReactMarkdown>{result}</ReactMarkdown> : <Text type="secondary">填写左侧信息后生成研究设计。</Text>}
              </div>
            </Spin>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
