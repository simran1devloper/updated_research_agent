'use client'

import { useState, useRef, useEffect } from 'react'
import { useChatStore, useThreadStore, useSettingsStore, useTelemetryStore, type Message, type ExecutionStep } from '@/lib/store'
import { streamResearch, type SSEEvent } from '@/lib/api-client'
import { rectify, avoid, checkErrorRate } from '@/lib/observability'
import { Button } from '@/components/ui/button'
import { Send, Settings2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

interface MessageInputProps {
  threadId: string
  onLoadingChange?: (loading: boolean) => void
}

export function MessageInput({ threadId, onLoadingChange }: MessageInputProps) {
  const [input, setInput] = useState('')
  const [isExpanded, setIsExpanded] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [showBudget, setShowBudget] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const { addMessage, updateMessage } = useChatStore()
  const { upsertThread, incrementMessageCount, threads } = useThreadStore()
  const { budgetLimit, setBudgetLimit } = useSettingsStore()
  const { addTokens } = useTelemetryStore()

  const contentRef = useRef('')
  const executionPipelineRef = useRef<ExecutionStep[]>([])

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px'
    }
  }, [input])

  const setLoading = (v: boolean) => {
    setIsLoading(v)
    onLoadingChange?.(v)
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const query = input.trim()
    setInput('')
    setIsExpanded(false)
    setLoading(true)

    // Ensure thread exists in local store (server will create it via ensure_thread)
    const existingThread = threads.find((t) => t.id === threadId)
    if (!existingThread) {
      upsertThread({
        id: threadId,
        title: query.slice(0, 60),
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messageCount: 0,
      })
    }

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: Date.now(),
    }
    addMessage(threadId, userMessage)
    incrementMessageCount(threadId)

    const assistantId = `msg_${Date.now()}_ai`
    addMessage(threadId, {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      executionPipeline: [],
    })

    const executionPath: string[] = []
    executionPipelineRef.current = []
    contentRef.current = ''
    let tokenUsage = 0

    try {
      // No history sent — server loads it from conversation-service
      await streamResearch(
        { query, thread_id: threadId, budget_limit: budgetLimit },
        (event: SSEEvent) => {
          if (event.type === 'node_start') {
            executionPath.push(event.node)
            const pipeline = executionPath.map((name, i) => ({
              id: `step_${i}`,
              name,
              status: (i === executionPath.length - 1 ? 'in-progress' : 'completed') as ExecutionStep['status'],
            }))
            executionPipelineRef.current = pipeline
            updateMessage(threadId, assistantId, { executionPipeline: pipeline })
          } else if (event.type === 'node_end') {
            const pipeline = executionPipelineRef.current.map((s) =>
              s.name === event.node ? { ...s, status: 'completed' as const } : s
            )
            executionPipelineRef.current = pipeline
            updateMessage(threadId, assistantId, { executionPipeline: pipeline })
          } else if (event.type === 'token') {
            contentRef.current += event.chunk
            updateMessage(threadId, assistantId, { content: contentRef.current })
          } else if (event.type === 'clarification') {
            contentRef.current = `**Clarification needed:** ${event.question}`
            updateMessage(threadId, assistantId, {
              content: contentRef.current,
              researchMeta: { isClarifying: true, executionPath },
            })
          } else if (event.type === 'done') {
            tokenUsage = event.token_usage
            updateMessage(threadId, assistantId, {
              researchMeta: {
                executionPath,
                sources: event.sources,
                mode: event.mode,
                iterations: event.iterations,
              },
              tokens: event.token_usage > 0 ? { input: event.token_usage, output: 0 } : undefined,
            })
            incrementMessageCount(threadId)
          } else if (event.type === 'error') {
            // RECTIFICATION: server-side error surfaced via SSE
            rectify(new Error(event.message), 'sse:server-error', { threadId, query: query.slice(0, 80) })
            updateMessage(threadId, assistantId, {
              content: `**Error:** ${event.message}`,
              isError: true,
            })
          }
        },
      )
      if (tokenUsage > 0) addTokens(threadId, tokenUsage, 0)
    } catch (err) {
      // RECTIFICATION: network / gateway failure
      rectify(err, 'streamResearch:catch', { threadId, query: query.slice(0, 80) })
      // AVOIDANCE: check if this operation is failing too often
      checkErrorRate('research:stream')
      updateMessage(threadId, assistantId, {
        content: `**Error contacting API Gateway:** ${err instanceof Error ? err.message : String(err)}`,
        isError: true,
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) handleSend()
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-2.5"
    >
      <div
        className={`border rounded-xl transition-all ${isExpanded ? 'border-primary/50 shadow-md shadow-primary/10' : 'border-border'}`}
        style={{ background: 'var(--input-bg)' }}
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onFocus={() => setIsExpanded(true)}
          onBlur={() => !input && setIsExpanded(false)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a research question… (Ctrl+Enter to send)"
          disabled={isLoading}
          className="w-full bg-transparent text-foreground placeholder-muted-foreground px-4 py-3 resize-none outline-none text-sm leading-relaxed disabled:opacity-50"
          rows={1}
        />
      </div>

      <div className="flex items-center justify-between">
        <div className="flex gap-2 items-center">
          <button
            onClick={() => setShowBudget((v) => !v)}
            className="text-muted-foreground hover:text-foreground transition-colors p-2 hover:bg-accent rounded-lg"
            title="Budget settings"
          >
            <Settings2 size={17} />
          </button>
          <AnimatePresence>
            {showBudget && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="flex items-center gap-2 overflow-hidden"
              >
                <label className="text-xs text-muted-foreground whitespace-nowrap">Budget:</label>
                <input
                  type="number"
                  value={budgetLimit}
                  onChange={(e) => setBudgetLimit(Number(e.target.value))}
                  min={100}
                  max={50000}
                  step={500}
                  className="w-24 bg-input border border-border text-foreground text-xs px-2 py-1 rounded outline-none focus:border-primary/50"
                />
                <span className="text-xs text-muted-foreground whitespace-nowrap">tokens</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <Button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed text-primary-foreground rounded-lg flex items-center gap-2 text-sm font-medium shadow-sm"
        >
          {isLoading ? (
            <div className="flex gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-primary-foreground animate-bounce" />
              <div className="w-1.5 h-1.5 rounded-full bg-primary-foreground animate-bounce delay-100" />
              <div className="w-1.5 h-1.5 rounded-full bg-primary-foreground animate-bounce delay-200" />
            </div>
          ) : (
            <>
              <Send size={15} />
              Send
            </>
          )}
        </Button>
      </div>

      {isExpanded && (
        <p className="text-xs text-muted-foreground px-1">
          Press <kbd className="bg-muted border border-border px-1.5 py-0.5 rounded text-xs font-mono">Ctrl+Enter</kbd> to send
        </p>
      )}
    </motion.div>
  )
}
