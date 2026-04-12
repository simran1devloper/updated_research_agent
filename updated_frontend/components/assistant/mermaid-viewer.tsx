'use client'

import { useEffect, useRef } from 'react'
import mermaid from 'mermaid'

interface MermaidViewerProps {
  code: string
}

let initialized = false

function isLikelyComplete(code: string): boolean {
  const trimmed = code.trim()
  // Must have at least 2 lines and not end mid-token
  const lines = trimmed.split('\n').filter(Boolean)
  if (lines.length < 2) return false
  // Incomplete if last line looks like a dangling arrow or label
  const last = lines[lines.length - 1].trim()
  if (/-->$|--$|\|$|\[$/.test(last)) return false
  return true
}

function sanitizeMermaidCode(code: string): string {
  code = code.trim()
  code = code.replace(/^```(?:mermaid)?\s*\n?/i, '').replace(/\n?```\s*$/i, '').trim()
  code = code.replace(/\["([^"]*?)"\]/g, (_, inner) =>
    `["${inner.replace(/\\n/g, ' ').replace(/\\t/g, ' ')}"]`
  )
  code = code.replace(/(--[->.]+)\s*\n\s*(\|[^|]+\|)/g, '$1$2')
  code = code.replace(/(--[->.]+)\s+\|/g, '$1|')
  code = code.replace(/--->/g, '-->')
  code = code
    .split('\n')
    .filter((l) => !/^\s*(style|classDef|class|linkStyle)\s+/i.test(l))
    .join('\n')
  const validStarts = [
    'graph ', 'graph\n', 'flowchart ', 'flowchart\n',
    'sequencediagram', 'classdiagram', 'statediagram',
    'erdiagram', 'gantt', 'pie', 'journey', 'gitgraph', 'mindmap', 'timeline',
  ]
  if (!validStarts.some((s) => code.split('\n')[0].trim().toLowerCase().startsWith(s))) {
    code = 'flowchart TD\n' + code
  }
  return code.trim()
}

export function MermaidViewer({ code }: MermaidViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastRenderedRef = useRef<string>('')

  useEffect(() => {
    if (!initialized) {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        securityLevel: 'loose',
        themeVariables: {
          primaryColor: '#1f6feb',
          primaryTextColor: '#c9d1d9',
          primaryBorderColor: '#388bfd',
          lineColor: '#8b949e',
          background: '#0d1117',
          mainBkg: '#161b22',
        },
      })
      initialized = true
    }
  }, [])

  useEffect(() => {
    // Debounce: wait 400ms of no new chunks before attempting render
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(async () => {
      if (!containerRef.current) return
      if (!isLikelyComplete(code)) return  // silently skip incomplete code
      const sanitized = sanitizeMermaidCode(code)
      if (sanitized === lastRenderedRef.current) return  // no change
      try {
        const id = `mermaid-${Math.random().toString(36).slice(2)}`
        const { svg } = await mermaid.render(id, sanitized)
        lastRenderedRef.current = sanitized
        containerRef.current.innerHTML = svg
      } catch {
        // Silently ignore parse errors during streaming — will retry on next chunk
      }
    }, 400)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [code])

  return (
    <div
      ref={containerRef}
      className="bg-gray-900 border border-gray-600/30 rounded-lg p-4 overflow-x-auto flex justify-center items-center"
      style={{ minHeight: '120px' }}
    />
  )
}
