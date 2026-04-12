'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism'
import dynamic from 'next/dynamic'

const MermaidViewer = dynamic(() => import('./mermaid-viewer').then((mod) => mod.MermaidViewer), {
  loading: () => <div className="bg-muted rounded p-4 text-sm text-muted-foreground">Loading diagram...</div>,
})

interface ContentRendererProps {
  content: string
}

export function ContentRenderer({ content }: ContentRendererProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '')
          const language = match ? match[1] : ''
          const isBlock = String(children).includes('\n') || !!language

          if (language === 'mermaid') {
            return (
              <div className="my-4">
                <MermaidViewer code={String(children).replace(/\n$/, '')} />
              </div>
            )
          }

          if (isBlock && language) {
            return (
              <div className="my-4 rounded-lg overflow-hidden border border-border">
                <SyntaxHighlighter language={language} style={oneDark}>
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              </div>
            )
          }

          return (
            <code className="bg-muted px-1.5 py-0.5 rounded text-primary text-[0.85em] font-mono" {...props}>
              {children}
            </code>
          )
        },
        p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
        h1: ({ children }) => <h1 className="text-xl font-bold mb-3 text-foreground">{children}</h1>,
        h2: ({ children }) => <h2 className="text-lg font-semibold mb-2 text-foreground">{children}</h2>,
        h3: ({ children }) => <h3 className="text-base font-semibold mb-2 text-foreground">{children}</h3>,
        ul: ({ children }) => <ul className="list-disc list-inside mb-3 space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-inside mb-3 space-y-1">{children}</ol>,
        li: ({ children }) => <li className="mb-1">{children}</li>,
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-primary/40 pl-3 my-3 italic text-muted-foreground">
            {children}
          </blockquote>
        ),
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary/80 underline underline-offset-2">
            {children}
          </a>
        ),
        table: ({ children }) => (
          <div className="my-3 overflow-x-auto rounded-lg border border-border">
            <table className="w-full border-collapse text-sm">{children}</table>
          </div>
        ),
        thead: ({ children }) => <thead className="bg-muted/60">{children}</thead>,
        tbody: ({ children }) => <tbody className="divide-y divide-border/50">{children}</tbody>,
        tr: ({ children }) => <tr className="hover:bg-muted/30 transition-colors">{children}</tr>,
        th: ({ children }) => (
          <th className="px-3 py-2 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b border-border">{children}</th>
        ),
        td: ({ children }) => <td className="px-3 py-2 text-sm align-top">{children}</td>,
      }}
    >
      {content}
    </ReactMarkdown>
  )
}
