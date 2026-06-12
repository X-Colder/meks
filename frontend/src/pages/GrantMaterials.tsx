import { useState } from 'react'
import { Button, Card, Col, Form, Input, Row, Select, Spin, Typography, message } from 'antd'
import { FileProtectOutlined } from '@ant-design/icons'
import ReactMarkdown from 'react-markdown'
import { generateAIResponse } from '@/api/aiAssistant'
import '@/styles/chat-markdown.css'

const { Title, Text } = Typography

const materialOptions = [
  { value: 'proposal', label: '课题申请书' },
  { value: 'ethics', label: '伦理申请材料' },
  { value: 'crf', label: '病例报告表 CRF' },
  { value: 'sap', label: '统计分析计划 SAP' },
  { value: 'consent', label: '知情同意书' },
]

export default function GrantMaterials() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState('')

  const handleGenerate = async (values: { material_type: string; title: string; background?: string; design?: string; population?: string }) => {
    setLoading(true)
    setResult('')
    try {
      const material = materialOptions.find((item) => item.value === values.material_type)?.label || values.material_type
      const prompt = `请作为医院科研秘书和医学研究方法学顾问，生成以下科研材料草稿。

材料类型：${material}
项目名称：${values.title}
研究背景：${values.background || '未说明'}
研究设计：${values.design || '未说明'}
研究对象/数据来源：${values.population || '未说明'}

要求：
1. 输出结构完整，可供医生继续编辑
2. 使用正式、规范、适合医院科研管理场景的中文
3. 不编造具体伦理批号、基金编号或不存在的数据
4. 标出需要医生补充的信息
5. 使用 Markdown 标题和列表`
      setResult(await generateAIResponse(prompt))
    } catch {
      message.error('生成材料失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <Title level={4}><FileProtectOutlined /> 课题材料</Title>
      <Text type="secondary">快速生成课题申请、伦理、CRF、SAP 和知情同意书等科研文档草稿。</Text>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} lg={9}>
          <Card size="small" title="材料信息">
            <Form form={form} layout="vertical" onFinish={handleGenerate} initialValues={{ material_type: 'proposal' }}>
              <Form.Item name="material_type" label="材料类型" rules={[{ required: true }]}>
                <Select options={materialOptions} />
              </Form.Item>
              <Form.Item name="title" label="项目名称" rules={[{ required: true }]}>
                <Input placeholder="例如：炎症指标预测房颤消融术后复发的回顾性队列研究" />
              </Form.Item>
              <Form.Item name="background" label="研究背景">
                <Input.TextArea rows={3} />
              </Form.Item>
              <Form.Item name="design" label="研究设计">
                <Input.TextArea rows={3} />
              </Form.Item>
              <Form.Item name="population" label="研究对象/数据来源">
                <Input.TextArea rows={3} />
              </Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>生成材料草稿</Button>
            </Form>
          </Card>
        </Col>
        <Col xs={24} lg={15}>
          <Card size="small" title="材料草稿">
            <Spin spinning={loading}>
              <div className="chat-markdown" style={{ minHeight: 420 }}>
                {result ? <ReactMarkdown>{result}</ReactMarkdown> : <Text type="secondary">填写左侧信息后生成材料草稿。</Text>}
              </div>
            </Spin>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
