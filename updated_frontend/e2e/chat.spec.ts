/**
 * E2E: Chat panel — message input, SSE streaming, error handling,
 *                   budget settings, keyboard shortcuts
 * Runs in 'chromium' / 'firefox' projects (authenticated).
 */
import { test, expect } from '@playwright/test'
import { SidebarPOM, ChatPanelPOM } from './pages/index'
import {
  mockThreadsEmpty, mockMessages,
  mockResearchStream, mockResearchStreamError, mockResearchStreamGatewayError,
} from './utils/mocks'

test.beforeEach(async ({ page }) => {
  await mockThreadsEmpty(page)
  await page.goto('/')
  await expect(page.locator('text=Research Agent')).toBeVisible({ timeout: 10_000 })
  // Create a thread so the chat panel is active
  const sidebar = new SidebarPOM(page)
  await sidebar.createNewThread()
})

// ── Empty state ───────────────────────────────────────────────────────────────

test.describe('Empty state', () => {
  test('shows empty state before any messages', async ({ page }) => {
    const chat = new ChatPanelPOM(page)
    await expect(chat.emptyState).toBeVisible()
  })

  test('send button is disabled when input is empty', async ({ page }) => {
    const chat = new ChatPanelPOM(page)
    await expect(chat.sendBtn).toBeDisabled()
  })

  test('send button enables when text is typed', async ({ page }) => {
    const chat = new ChatPanelPOM(page)
    await chat.typeMessage('Hello')
    await expect(chat.sendBtn).toBeEnabled()
  })
})

// ── Message sending ───────────────────────────────────────────────────────────

test.describe('Message sending', () => {
  test('user message appears in chat after send', async ({ page }) => {
    await mockResearchStream(page, ['Test response.'])
    const chat = new ChatPanelPOM(page)
    await chat.sendMessage('What is AI?')
    await expect(page.getByText('What is AI?')).toBeVisible({ timeout: 5_000 })
  })

  test('assistant response appears after streaming completes', async ({ page }) => {
    await mockResearchStream(page, ['This is a ', 'mock response.'])
    const chat = new ChatPanelPOM(page)
    await chat.sendMessage('Tell me about LangGraph')
    await chat.waitForResponse()
    await expect(page.getByText('This is a mock response.')).toBeVisible({ timeout: 15_000 })
  })

  test('Ctrl+Enter sends the message', async ({ page }) => {
    await mockResearchStream(page, ['Keyboard response.'])
    const chat = new ChatPanelPOM(page)
    await chat.sendWithCtrlEnter('Keyboard test')
    await expect(page.getByText('Keyboard test')).toBeVisible({ timeout: 5_000 })
  })

  test('input clears after sending', async ({ page }) => {
    await mockResearchStream(page, ['ok'])
    const chat = new ChatPanelPOM(page)
    await chat.sendMessage('Clear me')
    await expect(chat.textarea).toHaveValue('')
  })

  test('send button is disabled while loading', async ({ page }) => {
    // Slow stream to observe loading state
    await page.route('**/research/run/stream', async (route) => {
      await new Promise((r) => setTimeout(r, 300))
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: {"type":"done","sources":[],"mode":"quick","iterations":1,"token_usage":0}\n\ndata: [DONE]\n\n',
      })
    })
    const chat = new ChatPanelPOM(page)
    await chat.typeMessage('Loading test')
    await chat.send()
    await expect(chat.sendBtn).toBeDisabled()
  })

  test('execution pipeline steps are shown during streaming', async ({ page }) => {
    await mockResearchStream(page, ['Pipeline response.'])
    const chat = new ChatPanelPOM(page)
    await chat.sendMessage('Show pipeline')
    // node_start events should render pipeline steps
    await expect(page.getByText('classify')).toBeVisible({ timeout: 8_000 })
  })

  test('done event shows mode badge', async ({ page }) => {
    await mockResearchStream(page, ['Done.'], 'quick')
    const chat = new ChatPanelPOM(page)
    await chat.sendMessage('Mode test')
    await chat.waitForResponse()
    await expect(page.getByText('QUICK')).toBeVisible({ timeout: 10_000 })
  })

  test('sources are shown after done event', async ({ page }) => {
    await mockResearchStream(page, ['With sources.'])
    const chat = new ChatPanelPOM(page)
    await chat.sendMessage('Sources test')
    await chat.waitForResponse()
    await expect(page.getByText(/sources/i)).toBeVisible({ timeout: 10_000 })
  })
})

// ── Error handling — RECTIFICATION ───────────────────────────────────────────

test.describe('Error handling (Rectification)', () => {
  test('SSE error event shows error message in chat', async ({ page }) => {
    await mockResearchStreamError(page, 'LLM timeout')
    const chat = new ChatPanelPOM(page)
    await chat.sendMessage('Trigger error')
    await chat.waitForResponse()
    await expect(page.getByText(/LLM timeout/i)).toBeVisible({ timeout: 10_000 })
  })

  test('gateway 502 shows error message in chat', async ({ page }) => {
    await mockResearchStreamGatewayError(page)
    const chat = new ChatPanelPOM(page)
    await chat.sendMessage('Gateway error test')
    await chat.waitForResponse()
    await expect(page.getByText(/error/i)).toBeVisible({ timeout: 10_000 })
  })

  test('error message has error styling', async ({ page }) => {
    await mockResearchStreamError(page, 'Service down')
    const chat = new ChatPanelPOM(page)
    await chat.sendMessage('Error style test')
    await chat.waitForResponse()
    // Error messages have destructive border/background
    const errorMsg = page.locator('[class*="destructive"]').first()
    await expect(errorMsg).toBeVisible({ timeout: 10_000 })
  })

  test('can send another message after an error', async ({ page }) => {
    await mockResearchStreamError(page, 'First error')
    const chat = new ChatPanelPOM(page)
    await chat.sendMessage('First message')
    await chat.waitForResponse()

    // Now mock a successful response
    await mockResearchStream(page, ['Recovery response.'])
    await chat.sendMessage('Recovery message')
    await chat.waitForResponse()
    await expect(page.getByText('Recovery response.')).toBeVisible({ timeout: 15_000 })
  })
})

// ── Budget settings ───────────────────────────────────────────────────────────

test.describe('Budget settings', () => {
  test('budget toggle shows/hides budget input', async ({ page }) => {
    const chat = new ChatPanelPOM(page)
    await expect(chat.budgetInput).not.toBeVisible()
    await chat.budgetToggle.click()
    await expect(chat.budgetInput).toBeVisible({ timeout: 3_000 })
    await chat.budgetToggle.click()
    await expect(chat.budgetInput).not.toBeVisible()
  })

  test('budget input has default value of 5000', async ({ page }) => {
    const chat = new ChatPanelPOM(page)
    await chat.budgetToggle.click()
    await expect(chat.budgetInput).toHaveValue('5000')
  })

  test('budget value is sent with research request', async ({ page }) => {
    let capturedBody: Record<string, unknown> = {}
    await page.route('**/research/run/stream', async (route) => {
      capturedBody = JSON.parse(route.request().postData() ?? '{}')
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: 'data: {"type":"done","sources":[],"mode":"quick","iterations":1,"token_usage":0}\n\ndata: [DONE]\n\n',
      })
    })
    const chat = new ChatPanelPOM(page)
    await chat.budgetToggle.click()
    await chat.budgetInput.fill('2000')
    await chat.sendMessage('Budget test')
    await chat.waitForResponse()
    expect(capturedBody.budget_limit).toBe(2000)
  })
})

// ── History loading ───────────────────────────────────────────────────────────

test.describe('History loading', () => {
  test('server messages are loaded when switching to a thread', async ({ page }) => {
    const GW = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? 'http://localhost:8000'
    await page.route(`${GW}/api/v1/conversations/threads`, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{
          id: 'hist-thread-1', user_id: 'uid-e2e',
          title: 'History Thread', created_at: new Date().toISOString(),
        }]),
      })
    )
    await mockMessages(page, 'hist-thread-1', [
      { role: 'user', content: 'Previous question' },
      { role: 'assistant', content: 'Previous answer' },
    ])
    await page.reload()
    await page.getByText('History Thread').click()
    await expect(page.getByText('Previous question')).toBeVisible({ timeout: 8_000 })
    await expect(page.getByText('Previous answer')).toBeVisible()
  })
})
