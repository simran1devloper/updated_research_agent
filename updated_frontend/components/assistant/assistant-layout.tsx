'use client'

import { ReactNode } from 'react'
import { Sidebar } from './sidebar'
import { ChatPanel } from './chat-panel'

interface AssistantLayoutProps {
  children?: ReactNode
}

export function AssistantLayout({ children }: AssistantLayoutProps) {
  return (
    <div className="app-shell flex h-screen">
      <div className="w-64 border-r border-[var(--sidebar-border-color)] bg-[var(--sidebar-bg)] backdrop-blur-sm flex flex-col shrink-0">
        <Sidebar />
      </div>
      <div className="flex-1 flex flex-col overflow-hidden">
        <ChatPanel />
      </div>
      {children}
    </div>
  )
}
