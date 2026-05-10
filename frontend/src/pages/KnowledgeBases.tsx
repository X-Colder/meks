import { useEffect, useState } from 'react'
import { Card, Button, Modal, Form, Input, Select, List, Tag, Typography, message } from 'antd'
import { PlusOutlined, DatabaseOutlined } from '@ant-design/icons'
import { knowledgeBasesApi, KnowledgeBase } from '@/api/knowledgeBases'

const { Title, Text } = Typography

export default function KnowledgeBases() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  const fetchKbs = async () => {
    setLoading(true)
    try {
      const res = await knowledgeBasesApi.list()
      setKbs(res.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchKbs() }, [])

  const handleCreate = async (values: any) => {
    await knowledgeBasesApi.create(values)
    message.success('知识库创建成功')
    setModalOpen(false)
    form.resetFields()
    fetchKbs()
  }

  const visibilityColor: Record<string, string> = {
    public: 'green',
    department: 'blue',
    private: 'default',
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4}>知识库管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新建知识库
        </Button>
      </div>

      <List
        loading={loading}
        grid={{ gutter: 16, xs: 1, sm: 2, md: 3, lg: 3 }}
        dataSource={kbs}
        renderItem={(kb) => (
          <List.Item>
            <Card hoverable>
              <Card.Meta
                avatar={<DatabaseOutlined style={{ fontSize: 32, color: '#1677ff' }} />}
                title={kb.name}
                description={
                  <>
                    <Text type="secondary">{kb.description || '暂无描述'}</Text>
                    <div style={{ marginTop: 8 }}>
                      <Tag color={visibilityColor[kb.visibility]}>{kb.visibility}</Tag>
                      <Tag>{kb.document_count} 篇文档</Tag>
                    </div>
                  </>
                }
              />
            </Card>
          </List.Item>
        )}
      />

      <Modal
        title="新建知识库"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input placeholder="例如: 心血管前沿研究" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="知识库用途描述" />
          </Form.Item>
          <Form.Item name="visibility" label="可见范围" initialValue="department">
            <Select
              options={[
                { value: 'public', label: '全院公开' },
                { value: 'department', label: '科室可见' },
                { value: 'private', label: '仅自己' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
