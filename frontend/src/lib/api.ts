// Hand-written mirror of the backend schemas (backend/app/api/schemas, domain/models.py).
// shortcut: no codegen (openapi-typescript needs TypeScript 5); generate types if the API grows.
const API_URL: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface Session {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export type DocumentStatus = 'pending' | 'ready' | 'failed'

export interface LibraryDocument {
  id: string
  filename: string
  page_count: number | null
  status: DocumentStatus
  error: string | null
  created_at: string
}

export type ChatEvent =
  | { type: 'token'; text: string }
  | { type: 'tool_start'; id: string; name: string; args: Record<string, unknown> }
  | { type: 'tool_end'; id: string; name: string; ok: boolean }
  | { type: 'done'; input_tokens: number; output_tokens: number; latency_ms: number }
  | { type: 'error'; code: string; message: string }

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init)
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null
    throw new ApiError(
      typeof body?.detail === 'string' ? body.detail : `Request failed (${res.status})`,
    )
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  listSessions: () => request<Session[]>('/sessions'),
  createSession: () => request<Session>('/sessions', json('POST', {})),
  renameSession: (id: string, title: string) =>
    request<Session>(`/sessions/${id}`, json('PATCH', { title })),
  deleteSession: (id: string) => request<void>(`/sessions/${id}`, { method: 'DELETE' }),
  listDocuments: () => request<LibraryDocument[]>('/documents'),
  uploadDocument: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<LibraryDocument>('/documents', { method: 'POST', body: form })
  },
  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: 'DELETE' }),
}

/** POSTs a message and yields the SSE events (EventSource cannot POST). */
export async function* streamMessage(sessionId: string, text: string): AsyncGenerator<ChatEvent> {
  const res = await fetch(`${API_URL}/sessions/${sessionId}/messages`, json('POST', { text }))
  if (!res.ok || !res.body) throw new ApiError(`Request failed (${res.status})`)
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) return
    buffer += value.replace(/\r\n/g, '\n')
    let end: number
    while ((end = buffer.indexOf('\n\n')) !== -1) {
      const lines = buffer.slice(0, end).split('\n')
      buffer = buffer.slice(end + 2)
      const event = lines.find((l) => l.startsWith('event:'))?.slice(6).trim()
      const data = lines
        .filter((l) => l.startsWith('data:'))
        .map((l) => l.slice(5).trimStart())
        .join('\n')
      if (event && data) yield { type: event, ...(JSON.parse(data) as object) } as ChatEvent
    }
  }
}
