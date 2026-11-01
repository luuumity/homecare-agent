export interface Health {
  status: string
  app_version: string
  api_version: string
  server_time: string
}

export interface VersionInfo {
  app_version: string
  api_version: string
  min_shell_version: string
}

export interface Diagnose {
  server_time: string
  timezone: string
  db: {
    path: string
    exists: boolean
    writable: boolean
    sqlite_version: string
    fts5_available: boolean
    fts5_trigram_available: boolean
    detail: string
    error: string | null
  }
  llm: {
    base_url: string
    model: string
    api_key_set: boolean
    configured: boolean
  }
}

export interface WebVersion {
  web_version: string
  min_shell_version: string
  built_at: string
}

export interface Item {
  id: string
  name: string
  location: string
  note: string | null
  created_by: string
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface Reminder {
  id: string
  title: string
  remind_at: string
  repeat_rule: 'none' | 'daily' | 'weekly' | 'weekdays'
  enabled: boolean
  created_by: string
  created_at: string
  updated_at: string
  last_fired_at: string | null
  deleted_at: string | null
}

export interface Contact {
  id: string
  name: string
  relation: string | null
  phone: string
  phone_desensitized: string
  sort_order: number
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface CallLog {
  id: string
  contact_id: string
  contact_name: string
  phone_desensitized: string
  status: string
  started_at: string | null
  ended_at: string | null
  duration_seconds: number | null
  note: string | null
  created_by: string
  created_at: string
}

export interface Confirmation {
  id: string
  kind: string
  entity_type: string
  entity_id: string
  payload: {
    proposed?: { kind?: string; subject?: string; content?: string }
    previous_confirmation_id?: string | null
    [key: string]: unknown
  }
  requested_by: string
  status: 'pending' | 'approved' | 'rejected' | 'expired' | string
  elder_confirmed_by: string | null
  elder_confirmed_at: string | null
  family_confirmed_by: string | null
  family_confirmed_at: string | null
  rejected_by: string | null
  reject_reason: string | null
  expires_at: string | null
  created_at: string
  updated_at: string
}

export interface ToolEvent {
  name: string
  ok: boolean
  error: string | null
}

export interface ChatResponse {
  reply: string
  message_id: string
  created_at: string
  tool_calls: ToolEvent[]
  pending_confirmation_ids: string[]
  compressed: boolean
}

export interface HistoryMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  tool_name: string | null
  tool_payload: string | null
  created_at: string
}

export interface ChatStatus {
  llm_configured: boolean
  model: string
  message_count: number
  by_role: Record<string, number>
  has_summary: boolean
  summary_count: number
  last_message_id: string | null
  last_summarized_message_id: string | null
}

export interface OkResponse {
  ok: boolean
  id: string
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface RequestOptions {
  method?: string
  body?: unknown
  actor?: 'family' | 'elder' | 'agent' | 'system'
  timeoutMs?: number
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), options.timeoutMs ?? 15000)
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (options.actor) {
    headers['X-Actor'] = options.actor
  }

  try {
    const response = await fetch(path, {
      method: options.method ?? 'GET',
      headers,
      credentials: 'same-origin',
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: controller.signal,
    })
    const text = await response.text()
    const payload = text ? JSON.parse(text) : null
    if (!response.ok) {
      const detail = payload && typeof payload.detail === 'string' ? payload.detail : null
      if (response.status === 401 && !path.includes('/auth/')) {
        window.dispatchEvent(new Event('homecare-auth-expired'))
      }
      throw new ApiError(detail ?? `请求失败：HTTP ${response.status}`, response.status)
    }
    return payload as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('请求超时，请稍后再试', 0)
    }
    if (error instanceof SyntaxError) {
      throw new ApiError('服务器返回了无法识别的数据', 0)
    }
    throw new ApiError('网络连接失败，请检查网络', 0)
  } finally {
    window.clearTimeout(timeout)
  }
}

const enc = encodeURIComponent

function query(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export const api = {
  health: () => request<Health>('/api/health'),
  version: () => request<VersionInfo>('/api/version'),
  diagnose: () => request<Diagnose>('/api/diagnose', { timeoutMs: 20000 }),
  webVersion: () => request<WebVersion>('/version.json'),

  items: {
    list: (q = '') =>
      request<Item[]>(`/api/v1/items${query({ q: q.trim(), limit: 100 })}`),
    create: (body: { name: string; location: string; note?: string | null }) =>
      request<Item>('/api/v1/items', { method: 'POST', body, actor: 'family', timeoutMs: 15000 }),
    update: (id: string, body: { name?: string; location?: string; note?: string | null }) =>
      request<Item>(`/api/v1/items/${enc(id)}`, { method: 'PATCH', body, actor: 'family' }),
    remove: (id: string) =>
      request<OkResponse>(`/api/v1/items/${enc(id)}`, { method: 'DELETE', actor: 'family' }),
  },

  reminders: {
    list: (enabled?: boolean) =>
      request<Reminder[]>(`/api/v1/reminders${query({ enabled, limit: 100 })}`),
    create: (body: { title: string; remind_at: string; repeat_rule: Reminder['repeat_rule'] }) =>
      request<Reminder>('/api/v1/reminders', {
        method: 'POST',
        body,
        actor: 'family',
      }),
    update: (id: string, body: { title?: string; remind_at?: string; repeat_rule?: string; enabled?: boolean }) =>
      request<Reminder>(`/api/v1/reminders/${enc(id)}`, { method: 'PATCH', body, actor: 'family' }),
    remove: (id: string) =>
      request<OkResponse>(`/api/v1/reminders/${enc(id)}`, { method: 'DELETE', actor: 'family' }),
  },

  contacts: {
    list: () => request<Contact[]>('/api/v1/contacts?limit=100'),
  },

  calls: {
    list: (limit = 10) => request<CallLog[]>(`/api/v1/calls${query({ limit })}`),
    create: (body: { contact_id: string; status: string; note?: string }) =>
      request<CallLog>('/api/v1/calls', { method: 'POST', body, actor: 'elder' }),
  },

  confirmations: {
    list: (status?: string) =>
      request<Confirmation[]>(`/api/v1/confirmations${query({ status, limit: 100 })}`),
    elderConfirm: (id: string) =>
      request<Confirmation>(`/api/v1/confirmations/${enc(id)}/elder-confirm`, {
        method: 'POST',
        actor: 'elder',
      }),
    familyConfirm: (id: string) =>
      request<Confirmation>(`/api/v1/confirmations/${enc(id)}/family-confirm`, {
        method: 'POST',
        actor: 'family',
      }),
    reject: (id: string, reason?: string) =>
      request<Confirmation>(`/api/v1/confirmations/${enc(id)}/reject`, {
        method: 'POST',
        body: { reason: reason ?? null },
        actor: 'family',
      }),
  },

  chat: {
    send: (text: string) =>
      request<ChatResponse>('/api/v1/chat', {
        method: 'POST',
        body: { text },
        actor: 'elder',
        timeoutMs: 70000,
      }),
    history: (limit = 50) => request<HistoryMessage[]>(`/api/v1/chat/history${query({ limit })}`),
    status: () => request<ChatStatus>('/api/v1/chat/status'),
  },
  auth: {
    login: (pin: string) =>
      request<{ ok: boolean; role: string }>('/api/v1/auth/login', {
        method: 'POST',
        body: { pin },
        timeoutMs: 15000,
      }),
    me: () => request<{ ok: boolean; role: string }>('/api/v1/auth/me'),
    logout: () => request<{ ok: boolean }>('/api/v1/auth/logout', { method: 'POST' }),
  },
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return String(error)
}
