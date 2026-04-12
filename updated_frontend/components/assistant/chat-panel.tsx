'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { useThreadStore, useChatStore, type Message } from '@/lib/store'
import { fetchMessages } from '@/lib/api-client'
import { ChatMessage } from './chat-message'
import { MessageInput } from './message-input'
import { TokenStats } from './token-stats'
import { motion } from 'framer-motion'
import { Sparkles, Loader } from 'lucide-react'

export function ChatPanel() {
  const { threads, currentThreadId } = useThreadStore()
  const { messages, setThreadMessages } = useChatStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const loadedThreads = useRef<Set<string>>(new Set())

  // Reset cache on logout (currentThreadId becomes null)
  const prevThreadId = useRef(currentThreadId)
  useEffect(() => {
    if (prevThreadId.current !== null && currentThreadId === null) {
      loadedThreads.current.clear()
    }
    prevThreadId.current = currentThreadId
  }, [currentThreadId])

  const currentThread = threads.find((t) => t.id === currentThreadId)
  const currentMessages = currentThreadId ? messages[currentThreadId] ?? [] : []

  // Load server history when switching to a thread for the first time
  const loadHistory = useCallback(async (threadId: string) => {
    if (loadedThreads.current.has(threadId)) return
    loadedThreads.current.add(threadId)
    setIsLoadingHistory(true)
    try {
      const serverMsgs = await fetchMessages(threadId, 50)
      if (serverMsgs.length > 0) {
        const mapped: Message[] = serverMsgs.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          timestamp: new Date(m.created_at).getTime(),
          fromServer: true,
        }))
        setThreadMessages(threadId, mapped)
      }
    } finally {
      setIsLoadingHistory(false)
    }
  }, [setThreadMessages])

  useEffect(() => {
    if (currentThreadId) loadHistory(currentThreadId)
  }, [currentThreadId, loadHistory])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [currentMessages])

  if (!currentThreadId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
        <div className="text-center space-y-4 max-w-sm">
          <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto">
            <Sparkles size={24} className="text-primary" />
          </div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">AI Research Agent</h1>
          <p className="text-sm leading-relaxed">Select a thread from the sidebar or create a new one to start your research session.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border px-6 py-3.5 backdrop-blur-sm" style={{ background: 'var(--header-bg)' }}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-base font-semibold text-foreground leading-tight">{currentThread?.title}</h1>
            <p className="text-xs text-muted-foreground mt-0.5">{currentMessages.length} messages</p>
          </div>
          <TokenStats threadId={currentThreadId} />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 px-6 py-5">
        {isLoadingHistory ? (
          <div className="flex justify-center py-10">
            <Loader size={18} className="animate-spin text-muted-foreground" />
          </div>
        ) : currentMessages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center space-y-2 text-muted-foreground">
              <p className="text-sm font-medium">No messages yet</p>
              <p className="text-xs">Start a conversation below</p>
            </div>
          </div>
        ) : (
          <>
            {currentMessages.map((msg, idx) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: msg.fromServer ? 0 : idx * 0.04 }}
              >
                <ChatMessage message={msg} />
              </motion.div>
            ))}
            {isLoading && (
              <div className="flex justify-start py-2 pl-1">
                <div className="flex gap-1.5 items-center px-4 py-3 rounded-xl bg-card border border-border">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce" />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce delay-100" />
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce delay-200" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="border-t border-border px-6 py-4 backdrop-blur-sm" style={{ background: 'var(--header-bg)' }}>
        <MessageInput threadId={currentThreadId} onLoadingChange={setIsLoading} />
      </div>
    </div>
  )
}
