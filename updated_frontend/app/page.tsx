import { AssistantLayout } from '@/components/assistant/assistant-layout'
import { AuthGuard } from '@/components/auth/auth-guard'

export const metadata = {
  title: 'AI Assistant',
  description: 'A modern AI assistant interface with thread management and execution pipelines',
}

export default function Home() {
  return (
    <AuthGuard>
      <AssistantLayout />
    </AuthGuard>
  )
}
