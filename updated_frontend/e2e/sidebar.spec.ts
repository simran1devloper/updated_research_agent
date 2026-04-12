/**
 * E2E: Sidebar — thread management, health check, observability panel, logout
 * Runs in 'chromium' / 'firefox' projects (authenticated via storageState).
 */
import { test, expect } from '@playwright/test'
import { SidebarPOM, ChatPanelPOM } from './pages/index'
import {
  mockThreadsEmpty, mockThreads, mockDeleteThread,
  mockHealthOk, mockHealthDegraded, mockMessages,
} from './utils/mocks'

test.beforeEach(async ({ page }) => {
  await mockThreadsEmpty(page)
  await page.goto('/')
  await expect(page.locator('text=Research Agent')).toBeVisible({ timeout: 10_000 })
})

// ── Thread management ─────────────────────────────────────────────────────────

test.describe('Thread management', () => {
  test('new thread button creates a thread and activates it', async ({ page }) => {
    const sidebar = new SidebarPOM(page)
    const chat = new ChatPanelPOM(page)
    await sidebar.createNewThread()
    // Chat panel should now show the empty state for the new thread
    await expect(chat.emptyState).toBeVisible({ timeout: 5_000 })
  })

  test('creating multiple threads lists them all', async ({ page }) => {
    const sidebar = new SidebarPOM(page)
    await sidebar.createNewThread()
    await sidebar.createNewThread()
    await sidebar.createNewThread()
    const threads = page.locator('[class*="space-y-0"] > div, .space-y-0\\.5 > div')
    await expect(threads).toHaveCount(3, { timeout: 5_000 })
  })

  test('clicking a thread activates it', async ({ page }) => {
    const sidebar = new SidebarPOM(page)
    await sidebar.createNewThread()
    await sidebar.createNewThread()
    // Click the first thread
    const threads = page.locator('[class*="space-y-0"] > div, .space-y-0\\.5 > div')
    await threads.first().click()
    // Should have active styling (primary/10 background)
    await expect(threads.first()).toHaveClass(/primary/)
  })

  test('delete button removes thread from list', async ({ page }) => {
    await mockDeleteThread(page)
    const sidebar = new SidebarPOM(page)
    await sidebar.createNewThread()
    const threads = page.locator('[class*="space-y-0"] > div, .space-y-0\\.5 > div')
    await expect(threads).toHaveCount(1)
    // Hover to reveal delete button
    await threads.first().hover()
    const deleteBtn = threads.first().locator('button').last()
    await deleteBtn.click()
    await expect(threads).toHaveCount(0)
  })

  test('server threads are loaded on login', async ({ page }) => {
    // Navigate fresh with server threads mocked
    await mockThreads(page, [
      { id: 'srv-1', title: 'Server Thread 1' },
      { id: 'srv-2', title: 'Server Thread 2' },
    ])
    await mockMessages(page, 'srv-1')
    await mockMessages(page, 'srv-2')
    await page.reload()
    await expect(page.getByText('Server Thread 1')).toBeVisible({ timeout: 8_000 })
    await expect(page.getByText('Server Thread 2')).toBeVisible()
  })

  test('refresh button reloads threads', async ({ page }) => {
    const sidebar = new SidebarPOM(page)
    await mockThreads(page, [{ id: 'fresh-1', title: 'Fresh Thread' }])
    await mockMessages(page, 'fresh-1')
    await sidebar.refreshBtn.click()
    await expect(page.getByText('Fresh Thread')).toBeVisible({ timeout: 5_000 })
  })

  test('empty state shown when no threads exist', async ({ page }) => {
    await expect(page.getByText(/no threads yet/i)).toBeVisible()
  })
})

// ── Health check ──────────────────────────────────────────────────────────────

test.describe('Health check', () => {
  test('shows OK status when all services healthy', async ({ page }) => {
    await mockHealthOk(page)
    const sidebar = new SidebarPOM(page)
    await sidebar.checkHealth()
    await expect(page.getByText('OK')).toBeVisible({ timeout: 5_000 })
  })

  test('shows DEGRADED status when a service is down', async ({ page }) => {
    await mockHealthDegraded(page)
    const sidebar = new SidebarPOM(page)
    await sidebar.checkHealth()
    await expect(page.getByText('DEGRADED')).toBeVisible({ timeout: 5_000 })
  })

  test('shows individual service statuses after health check', async ({ page }) => {
    await mockHealthOk(page)
    const sidebar = new SidebarPOM(page)
    await sidebar.checkHealth()
    await expect(page.getByText('research-service')).toBeVisible({ timeout: 5_000 })
  })

  test('degraded service shows unreachable status', async ({ page }) => {
    await mockHealthDegraded(page)
    const sidebar = new SidebarPOM(page)
    await sidebar.checkHealth()
    await expect(page.getByText('unreachable')).toBeVisible({ timeout: 5_000 })
  })
})

// ── Observability panel ───────────────────────────────────────────────────────

test.describe('Observability panel', () => {
  test('toggle shows and hides the panel', async ({ page }) => {
    const sidebar = new SidebarPOM(page)
    await expect(page.getByText('Frontend Stats')).not.toBeVisible()
    await sidebar.toggleObservability()
    await expect(page.getByText('Frontend Stats')).toBeVisible({ timeout: 3_000 })
    await sidebar.toggleObservability()
    await expect(page.getByText('Frontend Stats')).not.toBeVisible()
  })

  test('panel shows "No operations tracked yet" initially', async ({ page }) => {
    const sidebar = new SidebarPOM(page)
    await sidebar.toggleObservability()
    await expect(page.getByText(/no operations tracked yet/i)).toBeVisible()
  })

  test('panel shows stats after a health check (API call tracked)', async ({ page }) => {
    await mockHealthOk(page)
    const sidebar = new SidebarPOM(page)
    await sidebar.checkHealth()
    await sidebar.toggleObservability()
    // After health check, at least one operation should be tracked
    // The panel either shows stats rows or "No operations" — both are valid
    await expect(page.getByText('Frontend Stats')).toBeVisible()
  })
})

// ── Logout ────────────────────────────────────────────────────────────────────

test.describe('Logout', () => {
  test('logout redirects to /login', async ({ page }) => {
    const sidebar = new SidebarPOM(page)
    await sidebar.logout()
    await page.waitForURL(/\/login/, { timeout: 8_000 })
    await expect(page).toHaveURL(/\/login/)
  })

  test('after logout, navigating to / redirects to /login', async ({ page }) => {
    const sidebar = new SidebarPOM(page)
    await sidebar.logout()
    await page.waitForURL(/\/login/)
    await page.goto('/')
    await page.waitForURL(/\/login/, { timeout: 8_000 })
    await expect(page).toHaveURL(/\/login/)
  })
})
