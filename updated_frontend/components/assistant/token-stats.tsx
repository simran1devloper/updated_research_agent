'use client'

import { useTelemetryStore } from '@/lib/store'
import { motion } from 'framer-motion'
import { BarChart3 } from 'lucide-react'

interface TokenStatsProps {
  threadId: string
}

export function TokenStats({ threadId }: TokenStatsProps) {
  const { getThreadTokens, totalTokens } = useTelemetryStore()
  const threadTokens = getThreadTokens(threadId)
  const totalUsed = threadTokens.input + threadTokens.output

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="flex items-center gap-2"
    >
      <div className="bg-primary/8 border border-primary/15 rounded-lg px-3 py-2">
        <div className="flex items-center gap-2">
          <BarChart3 size={14} className="text-primary" />
          <div className="text-xs space-y-0.5">
            <p className="text-muted-foreground leading-none">Thread</p>
            <p className="text-primary font-semibold leading-none">{totalUsed.toLocaleString()}</p>
          </div>
        </div>
      </div>

      <div className="bg-violet-500/8 border border-violet-500/15 rounded-lg px-3 py-2">
        <div className="flex items-center gap-2">
          <BarChart3 size={14} className="text-violet-500" />
          <div className="text-xs space-y-0.5">
            <p className="text-muted-foreground leading-none">Total</p>
            <p className="text-violet-500 font-semibold leading-none">{(totalTokens.input + totalTokens.output).toLocaleString()}</p>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
