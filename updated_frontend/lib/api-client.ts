import { detect, rectify, avoid, prevent, checkErrorRate } from './observability'

const BASE_URL = (process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? 'http://localhost:8000').replace(/\/$/, '')
const AUTH_URL = (process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ?? 'http://localhost:8007')

// ── Token storage ─────────────────────────────────────────────────────────────

export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('access_token')
}

export function setTokens(access: string, refresh: string) {
  localStorage.setItem('access_token', access)
  localStorage.setItem('refresh_token', refresh)
}

export function clearTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

function authHeaders(): Record<string, string> {
  const token = getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// Serialize concurrent refresh attempts so the token is only refreshed once
let refreshPromise: Promise<boolean> | null = null

async function apiFetch(url: string, init: RequestInit = {}, swallowError = false): Promise<Response | undefined> {
  // PREVENTION: url must be non-empty
  prevent('apiFetch:url-non-empty', !!url, { url })

  const operation = `${(init.method ?? 'GET').toUpperCase()} ${url}`
  return detect(operation, async () => {
    const res = await fetch(url, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(init.headers ?? {}) },
    })
    if (res.status === 401) {
      if (!refreshPromise) refreshPromise = tryRefresh().finally(() => { refreshPromise = null })
      const refreshed = await refreshPromise
      if (refreshed) {
        const retry = await fetch(url, {
          ...init,
          headers: { 'Content-Type': 'application/json', ...authHeaders(), ...(init.headers ?? {}) },
        })
        if (retry.status === 401) {
          clearTokens()
          window.location.href = '/login'
          return
        }
        return retry
      }
      clearTokens()
      window.location.href = '/login'
      return
    }
    // AVOIDANCE: warn on 5xx before it becomes a pattern
    if (res.status >= 500) {
      avoid('http_5xx_rate', 1, 1, { url, status: res.status })
      checkErrorRate(operation)
    }
    return res
  }, { url }, swallowError)
}

async function tryRefresh(): Promise<boolean> {
  const refresh = localStorage.getItem('refresh_token')
  if (!refresh) return false
  try {
    const res = await fetch(`${AUTH_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    })
    if (!res.ok) return false
    const data = await res.json()
    // refresh_token may not rotate — keep the old one if not returned
    setTokens(data.access_token, data.refresh_token ?? refresh)
    return true
  } catch {
    return false
  }
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface AuthUser {
  id: string
  email: string
  username: string
  role: string
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export async function register(email: string, username: string, password: string): Promise<AuthUser> {
  // PREVENTION: all fields required
  prevent('register:fields-required', !!(email && username && password), { email })
  return detect('auth:register', async () => {
    const res = await fetch(`${AUTH_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, username, password }),
    })
    if (!res.ok) {
      const err = await res.json()
      throw new Error(err.detail ?? 'Registration failed')
    }
    return res.json()
  }, { email })
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  prevent('login:fields-required', !!(email && password), { email })
  return detect('auth:login', async () => {
    const res = await fetch(`${AUTH_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json()
      const error = new Error(err.detail ?? 'Login failed')
      rectify(error, 'auth:login', { email, status: res.status })
      throw error
    }
    return res.json()
  }, { email })
}

export async function logout(refreshToken: string): Promise<void> {
  await fetch(`${AUTH_URL}/auth/logout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  }).catch(() => {})
  clearTokens()
}

export function getOAuthUrl(provider: 'google' | 'github'): string {
  return `${AUTH_URL}/auth/oauth/${provider}`
}

// ── Conversations ─────────────────────────────────────────────────────────────

export interface ServerThread {
  id: string
  user_id: string
  title: string
  created_at: string
}

export interface ServerMessage {
  id: string
  thread_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export async function fetchThreads(): Promise<ServerThread[]> {
  // swallowError=true: backend unreachable is expected when services are down
  const res = await apiFetch(`${BASE_URL}/api/v1/conversations/threads`, {}, true)
  if (!res?.ok) return []
  return res.json()
}

export async function fetchMessages(threadId: string, limit = 50): Promise<ServerMessage[]> {
  const res = await apiFetch(`${BASE_URL}/api/v1/conversations/threads/${threadId}/messages?limit=${limit}`, {}, true)
  if (!res?.ok) return []
  return res.json()
}

export async function deleteServerThread(threadId: string): Promise<void> {
  await apiFetch(`${BASE_URL}/api/v1/conversations/threads/${threadId}`, { method: 'DELETE' }, true)
}

// ── Research ──────────────────────────────────────────────────────────────────

export interface ResearchRequest {
  query: string
  thread_id: string
  budget_limit?: number
}

export interface ResearchResponse {
  status: 'completed' | 'clarifying' | 'failed'
  final_report?: string
  clarification_question?: string
  mode?: string
  iterations?: number
  token_usage?: number
  execution_path?: string[]
  sources?: string[]
}

export type SSEEvent =
  | { type: 'node_start'; node: string }
  | { type: 'node_end'; node: string; output: Record<string, unknown> }
  | { type: 'report_start' }
  | { type: 'token'; chunk: string }
  | { type: 'clarification'; question: string }
  | { type: 'done'; sources: string[]; mode: string; iterations: number; token_usage: number }
  | { type: 'error'; message: string }

async function _readStream(res: Response, onEvent: (event: SSEEvent) => void, threadId: string): Promise<void> {
  const reader = res.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let parseErrors = 0
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      const raw = line.slice(6).trim()
      if (raw === '[DONE]') return
      try {
        onEvent(JSON.parse(raw) as SSEEvent)
      } catch {
        parseErrors++
        avoid('sse_parse_error_rate', parseErrors, 5, { thread_id: threadId })
      }
    }
  }
  checkErrorRate('research:stream')
}

export async function streamResearch(
  req: ResearchRequest,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  // PREVENTION: query must not be blank
  prevent('streamResearch:query-non-empty', !!req.query?.trim(), { thread_id: req.thread_id })

  const streamInit: RequestInit = {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ budget_limit: 5000, ...req }),
    signal,
  }

  await detect('research:stream', async () => {
    let res = await fetch(`${BASE_URL}/api/v1/research/run/stream`, streamInit)

    if (res.status === 401) {
      if (!refreshPromise) refreshPromise = tryRefresh().finally(() => { refreshPromise = null })
      const refreshed = await refreshPromise
      if (!refreshed) {
        clearTokens()
        window.location.href = '/login'
        return
      }
      res = await fetch(`${BASE_URL}/api/v1/research/run/stream`, {
        ...streamInit,
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
      })
      if (res.status === 401) {
        clearTokens()
        window.location.href = '/login'
        return
      }
    }

    if (!res.ok) {
      const text = await res.text()
      const err = new Error(`Gateway error ${res.status}: ${text}`)
      rectify(err, 'research:stream', { status: res.status, thread_id: req.thread_id })
      throw err
    }

    await _readStream(res, onEvent, req.thread_id)
  }, { thread_id: req.thread_id, query_len: req.query.length })
}

// ── Health ────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  overall: 'ok' | 'degraded' | 'unreachable'
  services?: Record<string, string>
  error?: string
}

export async function checkHealth(): Promise<HealthResponse> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/health/`, { signal: AbortSignal.timeout(5_000) })
    return res.json()
  } catch (err) {
    return { overall: 'unreachable', error: String(err) }
  }
}

export function getGatewayUrl() { return BASE_URL }
