'use client'

import { type ExecutionStep } from '@/lib/store'
import { motion } from 'framer-motion'
import { CheckCircle2, AlertCircle, Clock, Loader } from 'lucide-react'

interface ExecutionPipelineProps {
  steps: ExecutionStep[]
}

export function ExecutionPipeline({ steps }: ExecutionPipelineProps) {
  const getStatusIcon = (status: ExecutionStep['status']) => {
    switch (status) {
      case 'completed': return <CheckCircle2 size={13} className="text-emerald-500" />
      case 'failed': return <AlertCircle size={13} className="text-destructive" />
      case 'in-progress': return <Loader size={13} className="text-primary animate-spin" />
      default: return <Clock size={13} className="text-muted-foreground" />
    }
  }

  const getStatusClass = (status: ExecutionStep['status']) => {
    switch (status) {
      case 'completed': return 'bg-emerald-500/8 border-emerald-500/20 text-emerald-600 dark:text-emerald-400'
      case 'failed': return 'bg-destructive/8 border-destructive/20 text-destructive'
      case 'in-progress': return 'bg-primary/8 border-primary/20 text-primary'
      default: return 'bg-muted border-border text-muted-foreground'
    }
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Execution Pipeline</p>
      <div className="flex flex-wrap gap-1.5">
        {steps.map((step, idx) => (
          <motion.div
            key={step.id}
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: idx * 0.08 }}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full border text-xs font-medium ${getStatusClass(step.status)}`}
            title={step.result}
          >
            {getStatusIcon(step.status)}
            <span>{step.name}</span>
            {step.duration && <span className="opacity-60">({step.duration}ms)</span>}
          </motion.div>
        ))}
      </div>
    </div>
  )
}
