/**
 * E2E: Accessibility + Theme
 * Covers: keyboard navigation, dark/light toggle, ARIA roles, focus management
 */
import { test, expect } from '@playwright/test'
import { SidebarPOM, ChatPanelPOM } from './pages/index'
import { mockThreadsEmpty, mockResearchStream } from './utils/mocks'

test.beforeEach(async ({ page }) => {
  await mockThreadsEmpty(page)
  await page.goto('/')
  await expect(page.locator('text=Research Agent')).toBeVisible({ timeout: 10_000 })
})

// ── Theme toggle ──────────────────────────────────────────────────────────────

test.describe('Theme', () => {
  test('theme toggle button is present', async ({ page }) => {
    // Sun or Moon icon button
    const themeBtn = page.locator('button').filter({ has: page.locator('svg') }).first()
    await expect(themeBtn).toBeVisible()
  })

  test('clicking theme toggle changes html class', async ({ page }) => {
    const html = page.locator('html')
    const before = await html.getAttribute('class')
    // Find the theme toggle (sun/moon button in sidebar header)
    const themeBtn = page.locator('button[class*="rounded-md"]').first()
    await themeBtn.click()
    const after = await html.getAttribute('class')
    // Class should have changed (dark ↔ light)
    expect(before).not.toBe(after)
  })
})

// ── Keyboard navigation ───────────────────────────────────────────────────────

test.describe('Keyboard navigation', () => {
  test('Tab key navigates through interactive elements on login page', async ({ page }) => {
    await page.goto('/login')
    await page.keyboard.press('Tab')
    // First focusable element should receive focus
    const focused = page.locator(':focus')
    await expect(focused).toBeVisible()
  })

  test('Ctrl+Enter sends message from textarea', async ({ page }) => {
    const sidebar = new SidebarPOM(page)
    await sidebar.createNewThread()
    await mockResearchStream(page, ['Keyboard sent.'])

    const chat = new ChatPanelPOM(page)
    await chat.textarea.focus()
    await chat.textarea.fill('Keyboard shortcut test')
    await page.keyboard.press('Control+Enter')
    await expect(page.getByText('Keyboard shortcut test')).toBeVisible({ timeout: 5_000 })
  })

  test('Escape does not submit the form', async ({ page }) => {
    const sidebar = new SidebarPOM(page)
    await sidebar.createNewThread()

    let requestMade = false
    await page.route('**/research/run/stream', () => { requestMade = true })

    const chat = new ChatPanelPOM(page)
    await chat.typeMessage('Should not send')
    await page.keyboard.press('Escape')
    expect(requestMade).toBe(false)
  })
})

// ── ARIA / semantic HTML ──────────────────────────────────────────────────────

test.describe('Accessibility', () => {
  test('login page has a submit button with accessible name', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
  })

  test('register page has a submit button with accessible name', async ({ page }) => {
    await page.goto('/register')
    await expect(page.getByRole('button', { name: /create account/i })).toBeVisible()
  })

  test('new thread button has accessible name', async ({ page }) => {
    await expect(page.getByRole('button', { name: /new thread/i })).toBeVisible()
  })

  test('send button has accessible name', async ({ page }) => {
    const sidebar = new SidebarPOM(page)
    await sidebar.createNewThread()
    await expect(page.getByRole('button', { name: /send/i })).toBeVisible()
  })

  test('page title is set correctly', async ({ page }) => {
    await expect(page).toHaveTitle(/AI/)
  })

  test('login page title is set', async ({ page }) => {
    await page.goto('/login')
    await expect(page).toHaveTitle(/AI/)
  })
})

// ── Responsive layout ─────────────────────────────────────────────────────────

test.describe('Layout', () => {
  test('sidebar is visible on desktop', async ({ page }) => {
    await expect(page.locator('text=Research Agent')).toBeVisible()
    await expect(page.getByRole('button', { name: /new thread/i })).toBeVisible()
  })

  test('chat panel is visible when thread is selected', async ({ page }) => {
    const sidebar = new SidebarPOM(page)
    await sidebar.createNewThread()
    const chat = new ChatPanelPOM(page)
    await expect(chat.textarea).toBeVisible()
    await expect(chat.sendBtn).toBeVisible()
  })

  test('no thread selected shows welcome state', async ({ page }) => {
    // No thread created — should show the welcome/empty state
    await expect(page.getByText(/AI Research Agent|select a thread/i)).toBeVisible()
  })
})
