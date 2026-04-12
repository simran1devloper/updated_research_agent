/**
 * Tests for lib/store.ts
 * Covers: AuthStore, ChatStore, ThreadStore, TelemetryStore, SettingsStore, HealthStore
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { act } from 'react'

// Import stores fresh — Vitest module isolation handles state
import {
  useAuthStore,
  useChatStore,
  useThreadStore,
  useTelemetryStore,
  useSettingsStore,
  useHealthStore,
  fromServer,
  type Message,
  type Thread,
} from '../../lib/store'
import type { ServerThread } from '../../lib/api-client'

// ── helpers ───────────────────────────────────────────────────────────────────

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: `msg-${Date.now()}-${Math.random()}`,
    role: 'user',
    content: 'Hello',
    timestamp: Date.now(),
    ...overrides,
  }
}

function makeThread(overrides: Partial<Thread> = {}): Thread {
  return {
    id: `thread-${Date.now()}`,
    title: 'Test Thread',
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messageCount: 0,
    ...overrides,
  }
}

// Reset stores before each test
beforeEach(() => {
  useAuthStore.setState({ user: null, isAuthenticated: false })
  useChatStore.setState({ messages: {} })
  useThreadStore.setState({ threads: [], currentThreadId: null, isLoadingThreads: false })
  useTelemetryStore.setState({ totalTokens: { input: 0, output: 0 }, threadTokens: {} })
  useSettingsStore.setState({ budgetLimit: 5000 })
  useHealthStore.setState({ health: null, isCheckingHealth: false })
})

// ═══════════════════════════════════════════════════════════════════════════════
// AuthStore
// ═══════════════════════════════════════════════════════════════════════════════

describe('useAuthStore', () => {
  it('initial state: unauthenticated', () => {
    const { user, isAuthenticated } = useAuthStore.getState()
    expect(user).toBeNull()
    expect(isAuthenticated).toBe(false)
  })

  it('setUser authenticates the user', () => {
    const user = { id: 'u1', email: 'a@b.com', username: 'alice', role: 'user', is_active: true }
    useAuthStore.getState().setUser(user)
    expect(useAuthStore.getState().isAuthenticated).toBe(true)
    expect(useAuthStore.getState().user?.id).toBe('u1')
  })

  it('setUser(null) clears authentication', () => {
    const user = { id: 'u1', email: 'a@b.com', username: 'alice', role: 'user', is_active: true }
    useAuthStore.getState().setUser(user)
    useAuthStore.getState().setUser(null)
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(useAuthStore.getState().user).toBeNull()
  })

  it('logout clears user and auth state', () => {
    const user = { id: 'u1', email: 'a@b.com', username: 'alice', role: 'user', is_active: true }
    useAuthStore.getState().setUser(user)
    useAuthStore.getState().logout()
    expect(useAuthStore.getState().user).toBeNull()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// ChatStore
// ═══════════════════════════════════════════════════════════════════════════════

describe('useChatStore', () => {
  const THREAD = 'thread-1'

  it('addMessage appends to thread', () => {
    const msg = makeMessage()
    useChatStore.getState().addMessage(THREAD, msg)
    expect(useChatStore.getState().getThreadMessages(THREAD)).toHaveLength(1)
    expect(useChatStore.getState().getThreadMessages(THREAD)[0].id).toBe(msg.id)
  })

  it('addMessage creates thread array if not exists', () => {
    const msg = makeMessage()
    useChatStore.getState().addMessage('new-thread', msg)
    expect(useChatStore.getState().getThreadMessages('new-thread')).toHaveLength(1)
  })

  it('updateMessage patches existing message', () => {
    const msg = makeMessage({ content: 'original' })
    useChatStore.getState().addMessage(THREAD, msg)
    useChatStore.getState().updateMessage(THREAD, msg.id, { content: 'updated' })
    const updated = useChatStore.getState().getThreadMessages(THREAD)[0]
    expect(updated.content).toBe('updated')
  })

  it('updateMessage does not affect other messages', () => {
    const msg1 = makeMessage({ id: 'a', content: 'first' })
    const msg2 = makeMessage({ id: 'b', content: 'second' })
    useChatStore.getState().addMessage(THREAD, msg1)
    useChatStore.getState().addMessage(THREAD, msg2)
    useChatStore.getState().updateMessage(THREAD, 'a', { content: 'changed' })
    const msgs = useChatStore.getState().getThreadMessages(THREAD)
    expect(msgs.find((m) => m.id === 'b')!.content).toBe('second')
  })

  it('setThreadMessages replaces all messages', () => {
    useChatStore.getState().addMessage(THREAD, makeMessage())
    const newMsgs = [makeMessage({ content: 'fresh' })]
    useChatStore.getState().setThreadMessages(THREAD, newMsgs)
    expect(useChatStore.getState().getThreadMessages(THREAD)).toHaveLength(1)
    expect(useChatStore.getState().getThreadMessages(THREAD)[0].content).toBe('fresh')
  })

  it('clearThread empties the thread', () => {
    useChatStore.getState().addMessage(THREAD, makeMessage())
    useChatStore.getState().clearThread(THREAD)
    expect(useChatStore.getState().getThreadMessages(THREAD)).toHaveLength(0)
  })

  it('getThreadMessages returns empty array for unknown thread', () => {
    expect(useChatStore.getState().getThreadMessages('unknown')).toEqual([])
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// ThreadStore
// ═══════════════════════════════════════════════════════════════════════════════

describe('useThreadStore', () => {
  it('upsertThread adds new thread', () => {
    const t = makeThread({ id: 't1' })
    useThreadStore.getState().upsertThread(t)
    expect(useThreadStore.getState().threads).toHaveLength(1)
  })

  it('upsertThread updates existing thread', () => {
    const t = makeThread({ id: 't1', title: 'Old' })
    useThreadStore.getState().upsertThread(t)
    useThreadStore.getState().upsertThread({ ...t, title: 'New' })
    const threads = useThreadStore.getState().threads
    expect(threads).toHaveLength(1)
    expect(threads[0].title).toBe('New')
  })

  it('removeThread deletes by id', () => {
    useThreadStore.getState().upsertThread(makeThread({ id: 't1' }))
    useThreadStore.getState().upsertThread(makeThread({ id: 't2' }))
    useThreadStore.getState().removeThread('t1')
    expect(useThreadStore.getState().threads.map((t) => t.id)).not.toContain('t1')
  })

  it('removeThread clears currentThreadId if it was the removed thread', () => {
    useThreadStore.getState().upsertThread(makeThread({ id: 't1' }))
    useThreadStore.getState().setCurrentThread('t1')
    useThreadStore.getState().removeThread('t1')
    expect(useThreadStore.getState().currentThreadId).toBeNull()
  })

  it('setCurrentThread updates currentThreadId', () => {
    useThreadStore.getState().setCurrentThread('t99')
    expect(useThreadStore.getState().currentThreadId).toBe('t99')
  })

  it('incrementMessageCount increases count and updatedAt', () => {
    const t = makeThread({ id: 't1', messageCount: 0 })
    useThreadStore.getState().upsertThread(t)
    const before = useThreadStore.getState().threads[0].updatedAt
    useThreadStore.getState().incrementMessageCount('t1')
    const after = useThreadStore.getState().threads[0]
    expect(after.messageCount).toBe(1)
    expect(after.updatedAt).toBeGreaterThanOrEqual(before)
  })

  it('setLoadingThreads toggles flag', () => {
    useThreadStore.getState().setLoadingThreads(true)
    expect(useThreadStore.getState().isLoadingThreads).toBe(true)
    useThreadStore.getState().setLoadingThreads(false)
    expect(useThreadStore.getState().isLoadingThreads).toBe(false)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// fromServer helper
// ═══════════════════════════════════════════════════════════════════════════════

describe('fromServer', () => {
  it('maps ServerThread to Thread correctly', () => {
    const serverThread: ServerThread = {
      id: 'srv-1',
      user_id: 'u1',
      title: 'My Thread',
      created_at: '2024-01-15T10:00:00Z',
    }
    const t = fromServer(serverThread)
    expect(t.id).toBe('srv-1')
    expect(t.title).toBe('My Thread')
    expect(t.messageCount).toBe(0)
    expect(typeof t.createdAt).toBe('number')
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// TelemetryStore
// ═══════════════════════════════════════════════════════════════════════════════

describe('useTelemetryStore', () => {
  it('addTokens accumulates totals', () => {
    useTelemetryStore.getState().addTokens('t1', 100, 50)
    useTelemetryStore.getState().addTokens('t1', 200, 100)
    const total = useTelemetryStore.getState().totalTokens
    expect(total.input).toBe(300)
    expect(total.output).toBe(150)
  })

  it('addTokens tracks per-thread tokens', () => {
    useTelemetryStore.getState().addTokens('t1', 100, 0)
    useTelemetryStore.getState().addTokens('t2', 50, 25)
    expect(useTelemetryStore.getState().getThreadTokens('t1').input).toBe(100)
    expect(useTelemetryStore.getState().getThreadTokens('t2').input).toBe(50)
  })

  it('getThreadTokens returns zeros for unknown thread', () => {
    const tokens = useTelemetryStore.getState().getThreadTokens('unknown')
    expect(tokens).toEqual({ input: 0, output: 0 })
  })

  it('multiple threads do not interfere', () => {
    useTelemetryStore.getState().addTokens('ta', 10, 5)
    useTelemetryStore.getState().addTokens('tb', 20, 10)
    expect(useTelemetryStore.getState().getThreadTokens('ta').input).toBe(10)
    expect(useTelemetryStore.getState().getThreadTokens('tb').input).toBe(20)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// SettingsStore
// ═══════════════════════════════════════════════════════════════════════════════

describe('useSettingsStore', () => {
  it('default budget is 5000', () => {
    expect(useSettingsStore.getState().budgetLimit).toBe(5000)
  })

  it('setBudgetLimit updates value', () => {
    useSettingsStore.getState().setBudgetLimit(10000)
    expect(useSettingsStore.getState().budgetLimit).toBe(10000)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// HealthStore
// ═══════════════════════════════════════════════════════════════════════════════

describe('useHealthStore', () => {
  it('initial health is null', () => {
    expect(useHealthStore.getState().health).toBeNull()
  })

  it('setHealth stores health response', () => {
    useHealthStore.getState().setHealth({ overall: 'ok', services: { 'research-service': 'ok' } })
    expect(useHealthStore.getState().health?.overall).toBe('ok')
  })

  it('setCheckingHealth toggles flag', () => {
    useHealthStore.getState().setCheckingHealth(true)
    expect(useHealthStore.getState().isCheckingHealth).toBe(true)
  })

  it('degraded health is stored correctly', () => {
    useHealthStore.getState().setHealth({ overall: 'degraded', services: { 'search-service': 'unreachable' } })
    expect(useHealthStore.getState().health?.overall).toBe('degraded')
  })
})
