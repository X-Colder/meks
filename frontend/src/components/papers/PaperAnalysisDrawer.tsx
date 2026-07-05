import { useEffect, useRef, useState } from 'react'
import { Alert, Drawer, Empty, Spin, Typography } from 'antd'
import { paperAnalysisApi, PaperAnalysisResult } from '@/api/paperAnalysis'
import PaperAnalysisResultView from './PaperAnalysisResultView'

const { Text } = Typography

interface PaperAnalysisDrawerProps {
  documentId: string | null
  title: string
  open: boolean
  initialStatus?: string | null
  onClose: () => void
  onStatusChange?: (documentId: string, result: PaperAnalysisResult) => void
}

function isNotFound(error: unknown) {
  return (error as { response?: { status?: number } }).response?.status === 404
}

export default function PaperAnalysisDrawer({
  documentId,
  title,
  open,
  initialStatus,
  onClose,
  onStatusChange,
}: PaperAnalysisDrawerProps) {
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<PaperAnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  const applyResult = (data: PaperAnalysisResult) => {
    setResult(data)
    onStatusChange?.(data.document_id, data)
    if (data.status === 'failed') {
      setError(data.error_message || '论文鉴真失败，请稍后重试')
    }
  }

  const startPolling = (id: string) => {
    stopPolling()
    setGenerating(true)
    pollRef.current = setInterval(async () => {
      try {
        const res = await paperAnalysisApi.get(id)
        if (res.data.status === 'completed' || res.data.status === 'failed') {
          stopPolling()
          setGenerating(false)
          applyResult(res.data)
        }
      } catch {
        stopPolling()
        setGenerating(false)
        setError('获取论文鉴真结果失败，请稍后重试')
      }
    }, 3000)
  }

  useEffect(() => {
    if (!open || !documentId) return undefined

    let cancelled = false
    setLoading(true)
    setGenerating(false)
    setResult(null)
    setError(null)

    const load = async () => {
      try {
        const existing = await paperAnalysisApi.get(documentId)
        if (cancelled) return
        if (existing.data.status === 'completed' || existing.data.status === 'failed') {
          applyResult(existing.data)
          return
        }
        if (initialStatus !== 'completed') {
          await paperAnalysisApi.trigger(documentId)
        }
        if (!cancelled) startPolling(documentId)
      } catch (err) {
        if (cancelled) return
        if (isNotFound(err)) {
          try {
            await paperAnalysisApi.trigger(documentId)
            if (!cancelled) startPolling(documentId)
          } catch {
            if (!cancelled) setError('论文鉴真启动失败，请稍后重试')
          }
          return
        }
        setError('获取论文鉴真结果失败，请稍后重试')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()

    return () => {
      cancelled = true
      stopPolling()
    }
  }, [open, documentId, initialStatus])

  return (
    <Drawer
      title={`论文鉴真：${title || '未选择论文'}`}
      open={open}
      onClose={onClose}
      width={920}
    >
      <Spin spinning={loading}>
        {error && <Alert type="warning" showIcon message={error} style={{ marginBottom: 16 }} />}
        {generating && (
          <Alert
            type="info"
            showIcon
            message="论文鉴真生成中"
            description="系统正在后台生成完整的六维度鉴真结果，完成后会自动展示。"
            style={{ marginBottom: 16 }}
          />
        )}
        {result?.status === 'completed' ? (
          <PaperAnalysisResultView result={result} compact />
        ) : (
          !loading && !generating && !error && (
            <Empty description={<Text type="secondary">暂无鉴真结果</Text>} />
          )
        )}
      </Spin>
    </Drawer>
  )
}
