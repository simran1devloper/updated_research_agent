'use client'

import { type Message } from '@/lib/store'
import { ExecutionPipeline } from './execution-pipeline'
import { ContentRenderer } from './content-renderer'
import { motion } from 'framer-motion'
import { ExternalLink, AlertCircle } from 'lucide-react'

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const meta = message.researchMeta

  return (
    <motion.div
      initial={{ opacity: 0, x: isUser ? 20 : -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.25 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-2xl space-y-3 p-4 rounded-xl border text-sm leading-relaxed ${
          message.isError
            ? 'bg-destructive/5 border-destructive/20 rounded-tl-sm'
            : isUser
            ? 'rounded-tr-sm'
            : 'bg-card border-border rounded-tl-sm'
        }`}
        style={
          !message.isError && isUser
            ? { background: 'var(--msg-user-bg)', borderColor: 'var(--msg-user-border)' }
            : undefined
        }
      >
        {message.isError && (
          <div className="flex items-center gap-2 text-destructive text-xs font-medium">
            <AlertCircle size={13} />
            Connection Error
          </div>
        )}

        {message.thinking && (
          <details className="group cursor-pointer">
            <summary className="text-xs text-muted-foreground hover:text-foreground font-medium select-none">
              💭 Thinking Process
            </summary>
            <div className="mt-2 pl-3 border-l-2 border-border text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">
              {message.thinking}
            </div>
          </details>
        )}

        {message.executionPipeline && message.executionPipeline.length > 0 && (
          <ExecutionPipeline steps={message.executionPipeline} />
        )}

        <div className={isUser ? 'text-foreground' : 'text-foreground/90'}>
          <ContentRenderer content={message.content} />
        </div>

        {meta && (meta.mode || meta.iterations !== undefined) && (
          <div className="flex flex-wrap gap-2 pt-2 border-t border-border/60">
            {meta.mode && (
              <span className="text-xs bg-primary/10 border border-primary/20 text-primary px-2 py-0.5 rounded-full font-medium">
                {meta.mode.toUpperCase()}
              </span>
            )}
            {meta.iterations !== undefined && (
              <span className="text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 px-2 py-0.5 rounded-full font-medium">
                {meta.iterations} iterations
              </span>
            )}
            {meta.isClarifying && (
              <span className="text-xs bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 px-2 py-0.5 rounded-full font-medium">
                ⚠ Clarification needed
              </span>
            )}
          </div>
        )}

        {meta?.sources && meta.sources.length > 0 && (
          <details className="cursor-pointer">
            <summary className="text-xs text-muted-foreground hover:text-foreground font-medium select-none">
              🔗 Sources ({meta.sources.length})
            </summary>
            <ul className="mt-2 space-y-1 pl-1">
              {meta.sources.slice(0, 10).map((url, i) => (
                <li key={i} className="flex items-center gap-1.5">
                  <ExternalLink size={11} className="text-primary shrink-0" />
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary hover:text-primary/80 underline truncate max-w-xs"
                  >
                    {url}
                  </a>
                </li>
              ))}
            </ul>
          </details>
        )}

        {message.tokens && (
          <div className="text-xs text-muted-foreground pt-2 border-t border-border/60">
            {message.tokens.input.toLocaleString()} tokens used
          </div>
        )}

        <div className="text-xs text-muted-foreground/60">
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </motion.div>
  )
}
