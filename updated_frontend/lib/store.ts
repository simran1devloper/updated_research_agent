import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { HealthResponse, AuthUser, ServerThread, ServerMessage } from './api-client'

// ── Auth ──────────────────────────────────────────────────────────────────────

interface AuthStore {
  user: AuthUser | null
  isAuthenticated: boolean
  setUser: (user: AuthUser | null) => void
  logout: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      logout: () => set({ user: null, isAuthenticated: false }),
    }),
    { name: 'auth-store' }
  )
)

// ── Messages (local UI state only — source of truth is server) ────────────────

export interface ExecutionStep {
  id: string
  name: string
  status: 'pending' | 'in-progress' | 'completed' | 'failed'
  duration?: number
}

export interface ResearchMeta {
  mode?: string
  iterations?: number
  executionPath?: string[]
  sources?: string[]
  isClarifying?: boolean
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  executionPipeline?: ExecutionStep[]
  tokens?: { input: number; output: number }
  researchMeta?: ResearchMeta
  isError?: boolean
  fromServer?: boolean   // true = loaded from conversation-service, not streaming
}

interface ChatStore {
  messages: Record<string, Message[]>
  addMessage: (threadId: string, message: Message) => void
  updateMessage: (threadId: string, messageId: string, updates: Partial<Message>) => void
  setThreadMessages: (threadId: string, messages: Message[]) => void
  getThreadMessages: (threadId: string) => Message[]
  clearThread: (threadId: string) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: {},

  addMessage: (threadId, message) =>
    set((s) => ({ messages: { ...s.messages, [threadId]: [...(s.messages[threadId] ?? []), message] } })),

  updateMessage: (threadId, messageId, updates) =>
    set((s) => ({
      messages: {
        ...s.messages,
        [threadId]: (s.messages[threadId] ?? []).map((m) => m.id === messageId ? { ...m, ...updates } : m),
      },
    })),

  setThreadMessages: (threadId, messages) =>
    set((s) => ({ messages: { ...s.messages, [threadId]: messages } })),

  getThreadMessages: (threadId) => get().messages[threadId] ?? [],

  clearThread: (threadId) =>
    set((s) => ({ messages: { ...s.messages, [threadId]: [] } })),
}))

// ── Threads (server-backed) ───────────────────────────────────────────────────

export interface Thread {
  id: string
  title: string
  createdAt: number
  updatedAt: number
  messageCount: number
}

function fromServer(t: ServerThread): Thread {
  const ts = new Date(t.created_at).getTime()
  return { id: t.id, title: t.title, createdAt: ts, updatedAt: ts, messageCount: 0 }
}

interface ThreadStore {
  threads: Thread[]
  currentThreadId: string | null
  isLoadingThreads: boolean
  setThreads: (threads: Thread[]) => void
  setLoadingThreads: (v: boolean) => void
  upsertThread: (thread: Thread) => void
  removeThread: (id: string) => void
  setCurrentThread: (id: string | null) => void
  incrementMessageCount: (threadId: string) => void
}

export const useThreadStore = create<ThreadStore>((set, get) => ({
  threads: [],
  currentThreadId: null,
  isLoadingThreads: false,

  setThreads: (threads) => set({ threads }),
  setLoadingThreads: (v) => set({ isLoadingThreads: v }),

  upsertThread: (thread) =>
    set((s) => {
      const exists = s.threads.find((t) => t.id === thread.id)
      return {
        threads: exists
          ? s.threads.map((t) => t.id === thread.id ? { ...t, ...thread } : t)
          : [thread, ...s.threads],
      }
    }),

  removeThread: (id) =>
    set((s) => ({
      threads: s.threads.filter((t) => t.id !== id),
      currentThreadId: s.currentThreadId === id ? (s.threads.find((t) => t.id !== id)?.id ?? null) : s.currentThreadId,
    })),

  setCurrentThread: (id) => set({ currentThreadId: id }),

  incrementMessageCount: (threadId) =>
    set((s) => ({
      threads: s.threads.map((t) =>
        t.id === threadId ? { ...t, messageCount: t.messageCount + 1, updatedAt: Date.now() } : t
      ),
    })),
}))

// Re-export fromServer helper for use in components
export { fromServer }

// ── Telemetry ─────────────────────────────────────────────────────────────────

interface TelemetryStore {
  totalTokens: { input: number; output: number }
  threadTokens: Record<string, { input: number; output: number }>
  addTokens: (threadId: string, input: number, output: number) => void
  getThreadTokens: (threadId: string) => { input: number; output: number }
}

export const useTelemetryStore = create<TelemetryStore>((set, get) => ({
  totalTokens: { input: 0, output: 0 },
  threadTokens: {},
  addTokens: (threadId, input, output) =>
    set((s) => ({
      totalTokens: { input: s.totalTokens.input + input, output: s.totalTokens.output + output },
      threadTokens: {
        ...s.threadTokens,
        [threadId]: {
          input: (s.threadTokens[threadId]?.input ?? 0) + input,
          output: (s.threadTokens[threadId]?.output ?? 0) + output,
        },
      },
    })),
  getThreadTokens: (threadId) => get().threadTokens[threadId] ?? { input: 0, output: 0 },
}))

// ── Settings ──────────────────────────────────────────────────────────────────

interface SettingsStore {
  budgetLimit: number
  setBudgetLimit: (v: number) => void
}

export const useSettingsStore = create<SettingsStore>((set) => ({
  budgetLimit: 5000,
  setBudgetLimit: (v) => set({ budgetLimit: v }),
}))

// ── Health ────────────────────────────────────────────────────────────────────

interface HealthStore {
  health: HealthResponse | null
  isCheckingHealth: boolean
  setHealth: (h: HealthResponse) => void
  setCheckingHealth: (v: boolean) => void
}

export const useHealthStore = create<HealthStore>((set) => ({
  health: null,
  isCheckingHealth: false,
  setHealth: (h) => set({ health: h }),
  setCheckingHealth: (v) => set({ isCheckingHealth: v }),
}))
