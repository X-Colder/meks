import { useEffect, useState, useCallback } from 'react'
import { Drawer, Descriptions, Typography, Divider, Spin, Tag, Button, message } from 'antd'
import { TranslationOutlined } from '@ant-design/icons'
import { documentsApi, DocumentContentResponse } from '@/api/documents'

const { Paragraph } = Typography

interface Props {
  documentId: string | null
  open: boolean
  onClose: () => void
}

export default function DocumentDetail({ documentId, open, onClose }: Props) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<DocumentContentResponse | null>(null)
  const [translating, setTranslating] = useState(false)
  const [translatedAbstract, setTranslatedAbstract] = useState<string | null>(null)
  const [translatedContent, setTranslatedContent] = useState<string>('')
  const [translateProgress, setTranslateProgress] = useState('')
  const [showTranslation, setShowTranslation] = useState(false)

  useEffect(() => {
    if (open && documentId) {
      setLoading(true)
      setData(null)
      setTranslatedAbstract(null)
      setTranslatedContent('')
      setShowTranslation(false)
      setTranslateProgress('')
      documentsApi.getContent(documentId)
        .then((res) => setData(res.data))
        .catch(() => message.error('获取文档内容失败'))
        .finally(() => setLoading(false))
    }
  }, [open, documentId])

  const getToken = useCallback(() => {
    try { return JSON.parse(localStorage.getItem('meks-auth') || '{}').state?.accessToken || '' }
    catch { return '' }
  }, [])

  const handleTranslate = async () => {
    if (!documentId) return
    if (translatedContent) {
      setShowTranslation(!showTranslation)
      return
    }
    setTranslating(true)
    setShowTranslation(true)
    setTranslatedContent('')
    setTranslatedAbstract(null)

    try {
      const response = await fetch(`/api/v1/documents/${documentId}/translate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
      })

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              continue
            }
            if (line.startsWith('data: ')) {
              const raw = line.slice(6)
              if (!raw || raw === '') continue
              try {
                const payload = JSON.parse(raw)
                if (payload.content && !payload.index && payload.index !== 0) {
                  setTranslatedAbstract(payload.content)
                  setTranslateProgress('摘要翻译完成')
                } else if (payload.index !== undefined) {
                  setTranslatedContent(prev => prev + (prev ? '\n\n' : '') + payload.content)
                  setTranslateProgress(`正文翻译中 ${payload.index + 1}/${payload.total}`)
                }
              } catch {}
            }
          }
        }
      }
      setTranslateProgress('')
    } catch {
      message.error('翻译失败，请重试')
      setShowTranslation(false)
    } finally {
      setTranslating(false)
    }
  }

  const statusColor: Record<string, string> = {
    uploaded: 'default', processing: 'processing', indexed: 'success', failed: 'error',
  }

  return (
    <Drawer
      title={data?.title || '文档详情'}
      open={open}
      onClose={onClose}
      width={720}
      destroyOnClose
      extra={
        data && (
          <Button
            icon={<TranslationOutlined />}
            onClick={handleTranslate}
            loading={translating}
            type={showTranslation ? 'primary' : 'default'}
          >
            {translating ? translateProgress || '翻译中...' : showTranslation ? '显示原文' : translatedContent ? '显示翻译' : '翻译为中文'}
          </Button>
        )
      }
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
      ) : data ? (
        <>
          <Descriptions column={1} size="small">
            {data.authors && <Descriptions.Item label="作者">{data.authors}</Descriptions.Item>}
            {data.publication_date && <Descriptions.Item label="发表日期">{data.publication_date}</Descriptions.Item>}
            <Descriptions.Item label="状态"><Tag color={statusColor[data.status]}>{data.status}</Tag></Descriptions.Item>
          </Descriptions>

          {data.abstract && (
            <>
              <Divider orientation="left">{showTranslation && translatedAbstract ? '摘要（中文）' : '摘要'}</Divider>
              <Paragraph style={{ background: showTranslation && translatedAbstract ? '#f0f7ff' : '#f5f5f5', padding: 12, borderRadius: 6, borderLeft: showTranslation && translatedAbstract ? '3px solid #1677ff' : 'none' }}>
                {showTranslation && translatedAbstract ? translatedAbstract : data.abstract}
              </Paragraph>
            </>
          )}

          <Divider orientation="left">{showTranslation ? '正文（中文）' : '正文内容'}{translateProgress && ` — ${translateProgress}`}</Divider>
          <div style={{ maxHeight: '60vh', overflow: 'auto' }}>
            <Paragraph style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
              {showTranslation ? (translatedContent || (translating ? '等待翻译...' : '暂无翻译')) : (data.content || '暂无正文内容')}
            </Paragraph>
          </div>
        </>
      ) : null}
    </Drawer>
  )
}
