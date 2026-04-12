'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useTheme } from 'next-themes'
import { useThreadStore, useHealthStore, useAuthStore, useChatStore, fromServer } from '@/lib/store'
import { checkHealth, fetchThreads, deleteServerThread, logout, getGatewayUrl, getAccessToken } from '@/lib/api-client'
import { recentIssues, stats } from '@/lib/observability'
import { Button } from '@/components/ui/button'
import {
  Plus, Trash2, Activity, CheckCircle2, XCircle, AlertTriangle,
  Loader, Sun, Moon, BrainCircuit, LogOut, User, RefreshCw, Bug,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

export function Sidebar() {
  const router = useRouter()
  const { threads, currentThreadId, setThreads, setCurrentThread, removeThread, upsertThread, isLoadingThreads, setLoadingThreads } = useThreadStore()
  const { clearThread } = useChatStore()
  const { health, isCheckingHealth, setHealth, setCheckingHealth } = useHealthStore()
  const { user, logout: authLogout } = useAuthStore()
  const [mounted, setMounted] = useState(false)
  const [showObsPanel, setShowObsPanel] = useState(false)
  const { theme, setTheme } = useTheme()

  useEffect(() => setMounted(true), [])

  const loadThreads = useCallback(async () => {
    if (!getAccessToken()) return
    setLoadingThreads(true)
    try {
      const serverThreads = await fetchThreads()
      setThreads(serverThreads.map(fromServer))
    } finally {
      setLoadingThreads(false)
    }
  }, [setThreads, setLoadingThreads])

  const userId = user?.id ?? null

  const prevUserId = useRef<string | null>(null)
  useEffect(() => {
    if (userId && userId !== prevUserId.current) {
      prevUserId.current = userId
      loadThreads()
    }
    if (!userId) prevUserId.current = null
  }, [userId, loadThreads])

  const handleNewThread = () => {
    const id = `thread_${Date.now()}`
    const thread = { id, title: `Thread ${new Date().toLocaleDateString()}`, createdAt: Date.now(), updatedAt: Date.now(), messageCount: 0 }
    upsertThread(thread)
    setCurrentThread(id)
  }

  const handleDeleteThread = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    removeThread(id)
    clearThread(id)
    await deleteServerThread(id).catch(() => {})
  }

  const handleLogout = async () => {
    const refresh = localStorage.getItem('refresh_token') ?? ''
    await logout(refresh)
    authLogout()
    setThreads([])
    setCurrentThread(null)
    router.push('/login')
  }

  const handleCheckHealth = async () => {
    setCheckingHealth(true)
    setHealth(await checkHealth())
    setCheckingHealth(false)
  }

  const overallIcon = () => {
    if (!health) return null
    if (health.overall === 'ok') return <CheckCircle2 size={13} className="text-emerald-500" />
    if (health.overall === 'degraded') return <AlertTriangle size={13} className="text-amber-500" />
    return <XCircle size={13} className="text-red-500" />
  }

  const overallColor = () => {
    if (!health) return 'text-muted-foreground'
    if (health.overall === 'ok') return 'text-emerald-500'
    if (health.overall === 'degraded') return 'text-amber-500'
    return 'text-red-500'
  }

  return (
    <div className="flex flex-col h-full">
      {/* Brand header */}
      <div className="px-4 py-4 border-b border-[var(--sidebar-border-color)]">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center shadow-sm">
              <BrainCircuit size={15} className="text-primary-foreground" />
            </div>
            <span className="text-sm font-semibold text-foreground tracking-tight">Research Agent</span>
          </div>
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
          >
            {mounted && (theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />)}
          </button>
        </div>
        <Button
          onClick={handleNewThread}
          className="w-full bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg flex items-center justify-center gap-2 text-sm font-medium shadow-sm"
        >
          <Plus size={16} />
          New Thread
        </Button>
      </div>

      {/* Threads list */}
      <div className="flex-1 overflow-y-auto py-2">
        <div className="flex items-center justify-between px-4 py-1.5">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Threads</span>
          <button onClick={loadThreads} className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors" title="Refresh">
            <RefreshCw size={12} className={isLoadingThreads ? 'animate-spin' : ''} />
          </button>
        </div>

        {isLoadingThreads && threads.length === 0 ? (
          <div className="flex justify-center py-6">
            <Loader size={16} className="animate-spin text-muted-foreground" />
          </div>
        ) : threads.length === 0 ? (
          <div className="px-4 py-8 text-center text-muted-foreground text-xs space-y-1">
            <p className="font-medium">No threads yet</p>
            <p>Create one to get started</p>
          </div>
        ) : (
          <div className="px-2 space-y-0.5">
            {threads.map((thread) => (
              <div
                key={thread.id}
                className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-all ${
                  currentThreadId === thread.id
                    ? 'bg-primary/10 text-foreground border border-primary/20'
                    : 'hover:bg-accent text-muted-foreground hover:text-foreground'
                }`}
                onClick={() => setCurrentThread(thread.id)}
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate font-medium">{thread.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(thread.createdAt).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={(e) => handleDeleteThread(e, thread.id)}
                  className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-destructive/10 text-muted-foreground hover:text-destructive rounded transition-all"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Bottom: health + user */}
      <div className="px-4 py-4 border-t border-[var(--sidebar-border-color)] space-y-3">
        {/* Health */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Activity size={13} className="text-muted-foreground" />
            <span className="text-xs font-medium text-muted-foreground">Service Health</span>
          </div>
          {health && (
            <div className={`flex items-center gap-1 text-xs font-semibold ${overallColor()}`}>
              {overallIcon()}
              {health.overall.toUpperCase()}
            </div>
          )}
        </div>

        <Button
          onClick={handleCheckHealth}
          disabled={isCheckingHealth}
          variant="outline"
          className="w-full text-xs border-border text-muted-foreground hover:bg-accent hover:text-foreground flex items-center gap-2"
        >
          {isCheckingHealth ? <Loader size={13} className="animate-spin" /> : <Activity size={13} />}
          {isCheckingHealth ? 'Checking…' : 'Check Health'}
        </Button>

        <AnimatePresence>
          {health?.services && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-1 overflow-hidden"
            >
              {Object.entries(health.services).map(([name, status]) => (
                <div key={name} className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground truncate">{name}</span>
                  <span className={status === 'ok' ? 'text-emerald-500' : 'text-red-500'}>
                    {status === 'ok' ? '✓' : '✗'} {status}
                  </span>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* User info + logout */}
        {user && (
          <div className="flex items-center justify-between pt-2 border-t border-border/50">
            <div className="flex items-center gap-2 min-w-0">
              <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                <User size={12} className="text-primary" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-foreground truncate">{user.username}</p>
                <p className="text-xs text-muted-foreground truncate">{user.email}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors shrink-0"
              title="Sign out"
            >
              <LogOut size={14} />
            </button>
          </div>
        )}

        <p className="text-xs text-muted-foreground/60 truncate">
          Gateway: <code className="text-muted-foreground">{getGatewayUrl()}</code>
        </p>

        {/* Observability panel toggle */}
        <button
          onClick={() => setShowObsPanel((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <Bug size={12} />
          {showObsPanel ? 'Hide' : 'Show'} Observability
        </button>

        <AnimatePresence>
          {showObsPanel && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden space-y-2"
            >
              {/* Frontend stats */}
              <div className="text-xs font-medium text-muted-foreground">Frontend Stats</div>
              {Object.entries(stats()).length === 0 ? (
                <p className="text-xs text-muted-foreground/60">No operations tracked yet.</p>
              ) : (
                Object.entries(stats()).map(([op, s]) => (
                  <div key={op} className="flex justify-between text-xs">
                    <span className="text-muted-foreground truncate max-w-[120px]" title={op}>{op}</span>
                    <span className={s.error_rate > 0.3 ? 'text-red-500' : s.error_rate > 0 ? 'text-amber-500' : 'text-emerald-500'}>
                      {s.errors}/{s.calls} ({(s.error_rate * 100).toFixed(0)}%)
                    </span>
                  </div>
                ))
              )}

              {/* Recent frontend issues */}
              {recentIssues(undefined, 5).length > 0 && (
                <>
                  <div className="text-xs font-medium text-muted-foreground pt-1">Recent Issues</div>
                  {recentIssues(undefined, 5).reverse().map((issue, i) => (
                    <div key={i} className="text-xs border border-border rounded p-1.5 space-y-0.5">
                      <div className="flex items-center gap-1">
                        <span className={`font-semibold ${
                          issue.stage === 'rectification' ? 'text-red-500' :
                          issue.stage === 'avoidance' ? 'text-amber-500' : 'text-blue-400'
                        }`}>[{issue.stage}]</span>
                        <span className="text-muted-foreground truncate">{issue.operation}</span>
                      </div>
                      <p className="text-muted-foreground/80 truncate" title={issue.message}>{issue.message}</p>
                    </div>
                  ))}
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
