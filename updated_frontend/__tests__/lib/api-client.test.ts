/**
 * Tests for lib/api-client.ts
 * Covers: prevention (blank query/fields), detection (fetch wrapping),
 *         avoidance (5xx), rectification (login failure, stream error)
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { recentIssues } from '../../lib/observability'

// Mock fetch globally
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => { store[k] = v },
    removeItem: (k: string) => { delete store[k] },
    clear: () => { store = {} },
  }
})()
vi.stubGlobal('localStorage', localStorageMock)

function makeResponse(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
    body: null,
  } as unknown as Response
}

beforeEach(() => {
  mockFetch.mockReset()
  localStorageMock.clear()
})

// ═══════════════════════════════════════════════════════════════════════════════
// Token helpers
// ═══════════════════════════════════════════════════════════════════════════════

describe('token helpers', () => {
  it('getAccessToken returns null when not set', async () => {
    const { getAccessToken } = await import('../../lib/api-client')
    expect(getAccessToken()).toBeNull()
  })

  it('setTokens stores both tokens', async () => {
    const { setTokens, getAccessToken } = await import('../../lib/api-client')
    setTokens('acc', 'ref')
    expect(getAccessToken()).toBe('acc')
    expect(localStorageMock.getItem('refresh_token')).toBe('ref')
  })

  it('clearTokens removes both tokens', async () => {
    const { setTokens, clearTokens, getAccessToken } = await import('../../lib/api-client')
    setTokens('acc', 'ref')
    clearTokens()
    expect(getAccessToken()).toBeNull()
    expect(localStorageMock.getItem('refresh_token')).toBeNull()
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// register — PREVENTION + DETECTION
// ═══════════════════════════════════════════════════════════════════════════════

describe('register', () => {
  it('PREVENTION: throws when email is empty', async () => {
    const { register } = await import('../../lib/api-client')
    await expect(register('', 'user', 'pass')).rejects.toThrow('Prevention failed')
  })

  it('PREVENTION: throws when username is empty', async () => {
    const { register } = await import('../../lib/api-client')
    await expect(register('a@b.com', '', 'pass')).rejects.toThrow('Prevention failed')
  })

  it('PREVENTION: throws when password is empty', async () => {
    const { register } = await import('../../lib/api-client')
    await expect(register('a@b.com', 'user', '')).rejects.toThrow('Prevention failed')
  })

  it('DETECTION: returns user on success', async () => {
    mockFetch.mockResolvedValueOnce(makeResponse(200, {
      id: 'u1', email: 'a@b.com', username: 'user', role: 'user', is_active: true,
    }))
    const { register } = await import('../../lib/api-client')
    const user = await register('a@b.com', 'user', 'pass')
    expect(user.id).toBe('u1')
  })

  it('DETECTION: throws on non-ok response', async () => {
    mockFetch.mockResolvedValueOnce(makeResponse(400, { detail: 'email taken' }))
    const { register } = await import('../../lib/api-client')
    await expect(register('dup@b.com', 'user', 'pass')).rejects.toThrow('email taken')
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// login — PREVENTION + DETECTION + RECTIFICATION
// ═══════════════════════════════════════════════════════════════════════════════

describe('login', () => {
  it('PREVENTION: throws when email is empty', async () => {
    const { login } = await import('../../lib/api-client')
    await expect(login('', 'pass')).rejects.toThrow('Prevention failed')
  })

  it('PREVENTION: throws when password is empty', async () => {
    const { login } = await import('../../lib/api-client')
    await expect(login('a@b.com', '')).rejects.toThrow('Prevention failed')
  })

  it('DETECTION: returns tokens on success', async () => {
    mockFetch.mockResolvedValueOnce(makeResponse(200, {
      access_token: 'acc', refresh_token: 'ref', token_type: 'bearer',
    }))
    const { login } = await import('../../lib/api-client')
    const tokens = await login('a@b.com', 'pass')
    expect(tokens.access_token).toBe('acc')
  })

  it('RECTIFICATION: records issue on 401 and throws', async () => {
    mockFetch.mockResolvedValueOnce(makeResponse(401, { detail: 'invalid credentials' }))
    const { login } = await import('../../lib/api-client')
    const before = recentIssues('rectification').length
    await expect(login('a@b.com', 'wrong')).rejects.toThrow('invalid credentials')
    expect(recentIssues('rectification').length).toBeGreaterThan(before)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// streamResearch — PREVENTION + DETECTION + AVOIDANCE + RECTIFICATION
// ═══════════════════════════════════════════════════════════════════════════════

describe('streamResearch', () => {
  it('PREVENTION: throws when query is blank', async () => {
    const { streamResearch } = await import('../../lib/api-client')
    await expect(streamResearch({ query: '   ', thread_id: 't1' }, vi.fn()))
      .rejects.toThrow('Prevention failed')
  })

  it('PREVENTION: throws when query is empty string', async () => {
    const { streamResearch } = await import('../../lib/api-client')
    await expect(streamResearch({ query: '', thread_id: 't1' }, vi.fn()))
      .rejects.toThrow('Prevention failed')
  })

  it('RECTIFICATION: records issue on gateway error', async () => {
    mockFetch.mockResolvedValueOnce(makeResponse(502, 'Bad Gateway'))
    const { streamResearch } = await import('../../lib/api-client')
    const before = recentIssues('rectification').length
    await expect(streamResearch({ query: 'test', thread_id: 't1' }, vi.fn()))
      .rejects.toThrow('Gateway error 502')
    expect(recentIssues('rectification').length).toBeGreaterThan(before)
  })

  it('DETECTION: parses SSE events and calls onEvent', async () => {
    const sseBody = [
      'data: {"type":"node_start","node":"classify"}\n\n',
      'data: {"type":"done","sources":[],"mode":"quick","iterations":1,"token_usage":10}\n\n',
      'data: [DONE]\n\n',
    ].join('')

    const encoder = new TextEncoder()
    const encoded = encoder.encode(sseBody)
    let offset = 0

    const mockReader = {
      read: vi.fn().mockImplementation(async () => {
        if (offset < encoded.length) {
          const chunk = encoded.slice(offset, offset + 50)
          offset += 50
          return { done: false, value: chunk }
        }
        return { done: true, value: undefined }
      }),
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      body: { getReader: () => mockReader },
    } as unknown as Response)

    const { streamResearch } = await import('../../lib/api-client')
    const events: unknown[] = []
    await streamResearch({ query: 'What is AI?', thread_id: 't1' }, (e) => events.push(e))
    expect(events.some((e: any) => e.type === 'node_start')).toBe(true)
    expect(events.some((e: any) => e.type === 'done')).toBe(true)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// checkHealth
// ═══════════════════════════════════════════════════════════════════════════════

describe('checkHealth', () => {
  it('returns ok response on success', async () => {
    mockFetch.mockResolvedValueOnce(makeResponse(200, { overall: 'ok', services: {} }))
    const { checkHealth } = await import('../../lib/api-client')
    const result = await checkHealth()
    expect(result.overall).toBe('ok')
  })

  it('returns unreachable on network error', async () => {
    mockFetch.mockRejectedValueOnce(new Error('network down'))
    const { checkHealth } = await import('../../lib/api-client')
    const result = await checkHealth()
    expect(result.overall).toBe('unreachable')
    expect(result.error).toContain('network down')
  })
})
