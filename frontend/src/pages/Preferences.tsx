import { Form, InputNumber, Select, Button, Typography, Card, message } from 'antd'
import { usePreferencesStore } from '@/stores/preferencesStore'

const { Title } = Typography

export default function Preferences() {
  const { defaultTopK, language, setDefaultTopK, setLanguage } = usePreferencesStore()

  const handleSave = (values: { defaultTopK: number; language: string }) => {
    setDefaultTopK(values.defaultTopK)
    setLanguage(values.language)
    message.success('偏好设置已保存')
  }

  return (
    <div>
      <Title level={4}>个人偏好</Title>
      <Card style={{ maxWidth: 480 }}>
        <Form
          layout="vertical"
          initialValues={{ defaultTopK, language }}
          onFinish={handleSave}
        >
          <Form.Item name="defaultTopK" label="默认检索结果数量">
            <InputNumber min={1} max={100} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="language" label="语言偏好">
            <Select
              options={[
                { value: 'zh', label: '中文' },
                { value: 'en', label: 'English' },
              ]}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              保存
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}
