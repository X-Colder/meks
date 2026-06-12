import { useEffect, useState } from 'react'
import { Card, Typography, Spin, Badge, Row, Col, Statistic } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { systemApi, ModelInfo, StorageStats, HealthStatus } from '@/api/system'

const { Title } = Typography

const statusIcon: Record<string, React.ReactNode> = {
  healthy: <CheckCircleOutlined style={{ color: '#52c41a' }} />,
  unhealthy: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
  degraded: <WarningOutlined style={{ color: '#faad14' }} />,
}

const statusBadge: Record<string, 'success' | 'error' | 'warning'> = {
  healthy: 'success',
  unhealthy: 'error',
  degraded: 'warning',
}

export default function SystemSettings() {
  const [models, setModels] = useState<ModelInfo[]>([])
  const [storage, setStorage] = useState<StorageStats | null>(null)
  const [health, setHealth] = useState<HealthStatus[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true)
      try {
        const [modelsRes, storageRes, healthRes] = await Promise.all([
          systemApi.getModels(),
          systemApi.getStorage(),
          systemApi.getHealth(),
        ])
        setModels(modelsRes.data)
        setStorage(storageRes.data)
        setHealth(healthRes.data)
      } finally {
        setLoading(false)
      }
    }
    fetchAll()
  }, [])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <Title level={4}>系统设置</Title>

      {/* Model Info */}
      <Title level={5}>模型信息</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {models.map((model) => (
          <Col xs={24} sm={12} md={8} key={model.name}>
            <Card>
              <Statistic
                title={model.type}
                value={model.name}
                suffix={
                  <Badge
                    status={model.status === 'running' ? 'processing' : 'default'}
                    text={model.status}
                  />
                }
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* Storage Stats */}
      <Title level={5}>存储统计</Title>
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {storage && (
          <>
            <Col xs={24} sm={8}>
              <Card title="MinIO 对象存储">
                <Statistic title="存储桶数量" value={storage.minio.bucket_count} />
                <Statistic title="总大小" value={storage.minio.total_size} style={{ marginTop: 12 }} />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card title="PostgreSQL">
                <Statistic title="总行数" value={storage.postgres.total_rows} />
                {Object.entries(storage.postgres.tables).map(([table, count]) => (
                  <Statistic key={table} title={table} value={count} style={{ marginTop: 12 }} />
                ))}
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card title="Milvus 向量库">
                <Statistic title="集合数量" value={storage.milvus.collection_count} />
                <Statistic title="向量总数" value={storage.milvus.total_vectors} style={{ marginTop: 12 }} />
              </Card>
            </Col>
          </>
        )}
      </Row>

      {/* Health Checks */}
      <Title level={5}>服务健康检查</Title>
      <Row gutter={[16, 16]}>
        {health.map((svc) => (
          <Col xs={24} sm={12} md={8} key={svc.service}>
            <Card>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {statusIcon[svc.status]}
                <span style={{ fontWeight: 'bold', fontSize: 16 }}>{svc.service}</span>
              </div>
              <div style={{ marginTop: 8 }}>
                <Badge status={statusBadge[svc.status]} text={svc.status} />
                <span style={{ marginLeft: 16, color: '#888' }}>{svc.latency_ms}ms</span>
              </div>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )
}
