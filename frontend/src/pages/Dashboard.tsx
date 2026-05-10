import { useEffect, useState } from 'react'
import { Card, Col, Row, Statistic, Typography } from 'antd'
import {
  DatabaseOutlined,
  FileTextOutlined,
  UserOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons'
import apiClient from '@/api/client'

const { Title } = Typography

interface Stats {
  users: number
  documents: number
  knowledge_bases: number
  indexed_documents: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    apiClient.get('/system/stats').then((res) => setStats(res.data)).catch(() => {})
  }, [])

  return (
    <div>
      <Title level={4}>工作台</Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="知识库" value={stats?.knowledge_bases || 0} prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="文档总数" value={stats?.documents || 0} prefix={<FileTextOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="已索引" value={stats?.indexed_documents || 0} prefix={<CheckCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="用户数" value={stats?.users || 0} prefix={<UserOutlined />} />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
