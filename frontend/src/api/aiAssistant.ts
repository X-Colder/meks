import { useAuthStore } from '@/stores/authStore'

export async function generateAIResponse(prompt: string): Promise<string> {
  const token = useAuthStore.getState().accessToken
  const sessionRes = await fetch('/api/v1/chat/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ knowledge_base_ids: [] }),
  })
  if (!sessionRes.ok) throw new Error('创建 AI 会话失败')
  const session = await sessionRes.json()

  const msgRes = await fetch(`/api/v1/chat/sessions/${session.id}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ content: prompt }),
  })
  if (!msgRes.ok) throw new Error('AI 请求失败')

  let fullResponse = ''
  const reader = msgRes.body?.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  if (!reader) return fullResponse

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      const cleaned = line.replace(/\r/g, '')
      if (cleaned.startsWith('event: done')) break
      if (cleaned.startsWith('data:')) {
        const payload = cleaned.substring(5)
        if (payload.trim() === '') fullResponse += '\n'
        else fullResponse += payload.startsWith(' ') ? payload.substring(1) : payload
      }
    }
  }
  return fullResponse
}
