import { useState, useRef, useEffect } from 'react'
import { Input, Card, List, Select, Typography, Button, Space, message } from 'antd'
import { SendOutlined, PlusOutlined } from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'
import { useKBStore } from '@/stores/knowledgeBaseStore'
import apiClient from '@/api/client'

const { Title, Text } = Typography

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function Chat() {
  const { kbs, fetchKbs } = useKBStore()
  const [selectedKbs, setSelectedKbs] = useState<string[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchKbs()
  }, [fetchKbs])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const createSession = async () => {
    if (selectedKbs.length === 0) return
    const res = await apiClient.post('/chat/sessions', {
      knowledge_base_ids: selectedKbs,
    })
    setSessionId(res.data.id)
    setMessages([])
  }

  const sendMessage = async () => {
    if (!input.trim() || !sessionId) return
    const userMsg = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }])
    setLoading(true)

    try {
      const token = useAuthStore.getState().accessToken
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ content: userMsg }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ''

      setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

      if (reader) {
        let currentEvent = ''
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7).trim()
            } else if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (currentEvent === 'token') {
                assistantContent += data
                setMessages((prev) => {
                  const updated = [...prev]
                  updated[updated.length - 1] = {
                    role: 'assistant',
                    content: assistantContent,
                  }
                  return updated
                })
              }
              currentEvent = ''
            }
          }
        }
      }
    } catch (error) {
      message.error('发送消息失败，请重试')
      setMessages((prev) => prev.filter((m) => m.content !== ''))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ height: 'calc(100vh - 200px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
        <Select
          mode="multiple"
          style={{ flex: 1 }}
          placeholder="选择知识库"
          onChange={setSelectedKbs}
          options={kbs.map((kb) => ({ value: kb.id, label: kb.name }))}
        />
        <Button icon={<PlusOutlined />} onClick={createSession} disabled={selectedKbs.length === 0}>
          新建对话
        </Button>
      </div>

      <Card style={{ flex: 1, overflow: 'auto', marginBottom: 16 }} styles={{ body: { padding: 16 } }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 48, color: '#999' }}>
            <Title level={5} type="secondary">选择知识库并创建对话开始提问</Title>
            <Text type="secondary">例如：近年来心脏瓣膜微创手术有哪些新进展？</Text>
          </div>
        ) : (
          <List
            dataSource={messages}
            renderItem={(msg) => (
              <div
                style={{
                  marginBottom: 16,
                  textAlign: msg.role === 'user' ? 'right' : 'left',
                }}
              >
                <div
                  style={{
                    display: 'inline-block',
                    maxWidth: '80%',
                    padding: '8px 16px',
                    borderRadius: 8,
                    background: msg.role === 'user' ? '#1677ff' : '#f5f5f5',
                    color: msg.role === 'user' ? '#fff' : '#000',
                  }}
                >
                  {msg.content || '...'}
                </div>
              </div>
            )}
          />
        )}
        <div ref={messagesEndRef} />
      </Card>

      <Space.Compact style={{ width: '100%' }}>
        <Input
          size="large"
          placeholder={sessionId ? '输入您的问题...' : '请先创建对话'}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={sendMessage}
          disabled={!sessionId || loading}
        />
        <Button
          type="primary"
          size="large"
          icon={<SendOutlined />}
          onClick={sendMessage}
          loading={loading}
          disabled={!sessionId}
        >
          发送
        </Button>
      </Space.Compact>
    </div>
  )
}
