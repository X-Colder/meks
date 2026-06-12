import { useEffect, useState } from 'react'
import { Upload, Select, Card, Table, Tag, Typography, message } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import { documentsApi, DocumentItem } from '@/api/documents'
import { knowledgeBasesApi, KnowledgeBase } from '@/api/knowledgeBases'
import DocumentDetail from '@/components/documents/DocumentDetail'

const { Dragger } = Upload
const { Title } = Typography

const statusMap: Record<string, { color: string; text: string }> = {
  uploaded: { color: 'default', text: '已上传' },
  processing: { color: 'processing', text: '处理中' },
  indexed: { color: 'success', text: '已索引' },
  failed: { color: 'error', text: '失败' },
}

export default function DocumentUpload() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([])
  const [selectedKb, setSelectedKb] = useState<string>('')
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [docsTotal, setDocsTotal] = useState(0)
  const [docsPage, setDocsPage] = useState(1)
  const [drawerDocId, setDrawerDocId] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  useEffect(() => {
    knowledgeBasesApi.list().then((res) => {
      setKbs(res.data)
      if (res.data.length > 0) setSelectedKb(res.data[0].id)
    })
  }, [])

  useEffect(() => {
    if (selectedKb) {
      documentsApi.list({ knowledge_base_id: selectedKb, page: docsPage, page_size: 10 }).then((res) => {
        setDocuments(res.data.items)
        setDocsTotal(res.data.total)
      })
    }
  }, [selectedKb, docsPage])

  const columns = [
    { title: '文件名', dataIndex: 'title', key: 'title' },
    { title: '类型', dataIndex: 'file_type', key: 'file_type', width: 80 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const s = statusMap[status] || { color: 'default', text: status }
        return <Tag color={s.color}>{s.text}</Tag>
      },
    },
    { title: '分块数', dataIndex: 'chunk_count', key: 'chunk_count', width: 80 },
    { title: '上传时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  ]

  return (
    <div>
      <Title level={4}>文档上传</Title>

      <Card style={{ marginBottom: 16 }}>
        <Select
          style={{ width: 300, marginBottom: 16 }}
          placeholder="选择目标知识库"
          value={selectedKb || undefined}
          onChange={(value) => { setSelectedKb(value); setDocsPage(1) }}
          options={kbs.map((kb) => ({ value: kb.id, label: kb.name }))}
        />

        <Dragger
          name="file"
          multiple
          accept=".pdf,.docx,.doc,.xml,.txt,.md"
          disabled={!selectedKb}
          customRequest={async ({ file, onSuccess, onError }) => {
            try {
              await documentsApi.upload(file as File, selectedKb)
              message.success(`${(file as File).name} 上传成功`)
              onSuccess?.({})
              setDocsPage(1)
              documentsApi.list({ knowledge_base_id: selectedKb, page: 1, page_size: 10 }).then((res) => {
                setDocuments(res.data.items)
                setDocsTotal(res.data.total)
              }
              )
            } catch (err: any) {
              message.error(`上传失败: ${err.response?.data?.detail || '未知错误'}`)
              onError?.(err)
            }
          }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">支持 PDF、DOCX、XML、TXT、Markdown 格式</p>
        </Dragger>
      </Card>

      <Card title="已上传文档">
        <Table
          columns={columns}
          dataSource={documents}
          rowKey="id"
          size="small"
          onRow={(record) => ({
            onClick: () => { setDrawerDocId(record.id); setDrawerOpen(true) },
            style: { cursor: 'pointer' },
          })}
          pagination={{
            current: docsPage,
            total: docsTotal,
            pageSize: 10,
            showSizeChanger: false,
            onChange: setDocsPage,
          }}
        />
      </Card>

      <DocumentDetail
        documentId={drawerDocId}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  )
}
