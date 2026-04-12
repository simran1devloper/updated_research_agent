/**
 * Page Object Models — one class per page/component.
 * All selectors live here; tests stay readable.
 */
import { type Page, type Locator, expect } from '@playwright/test'

// ── LoginPage ─────────────────────────────────────────────────────────────────

export class LoginPage {
  readonly page: Page
  readonly emailInput: Locator
  readonly passwordInput: Locator
  readonly submitBtn: Locator
  readonly errorMsg: Locator
  readonly registerLink: Locator
  readonly googleBtn: Locator
  readonly githubBtn: Locator

  constructor(page: Page) {
    this.page = page
    this.emailInput = page.getByPlaceholder('Email')
    this.passwordInput = page.getByPlaceholder('Password')
    this.submitBtn = page.getByRole('button', { name: /sign in/i })
    this.errorMsg = page.locator('p.text-destructive, [class*="destructive"]').first()
    this.registerLink = page.getByRole('link', { name: /create one/i })
    this.googleBtn = page.getByRole('link', { name: /google/i })
    this.githubBtn = page.getByRole('link', { name: /github/i })
  }

  async goto() {
    await this.page.goto('/login')
    await expect(this.submitBtn).toBeVisible()
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email)
    await this.passwordInput.fill(password)
    await this.submitBtn.click()
  }

  async expectError(text: string) {
    await expect(this.errorMsg).toContainText(text)
  }
}

// ── RegisterPage ──────────────────────────────────────────────────────────────

export class RegisterPage {
  readonly page: Page
  readonly emailInput: Locator
  readonly usernameInput: Locator
  readonly passwordInput: Locator
  readonly submitBtn: Locator
  readonly errorMsg: Locator
  readonly loginLink: Locator

  constructor(page: Page) {
    this.page = page
    this.emailInput = page.getByPlaceholder('Email')
    this.usernameInput = page.getByPlaceholder('Username')
    this.passwordInput = page.getByPlaceholder('Password')
    this.submitBtn = page.getByRole('button', { name: /create account/i })
    this.errorMsg = page.locator('p.text-destructive, [class*="destructive"]').first()
    this.loginLink = page.getByRole('link', { name: /sign in/i })
  }

  async goto() {
    await this.page.goto('/register')
    await expect(this.submitBtn).toBeVisible()
  }

  async register(email: string, username: string, password: string) {
    await this.emailInput.fill(email)
    await this.usernameInput.fill(username)
    await this.passwordInput.fill(password)
    await this.submitBtn.click()
  }
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

export class SidebarPOM {
  readonly page: Page
  readonly newThreadBtn: Locator
  readonly healthBtn: Locator
  readonly logoutBtn: Locator
  readonly obsToggle: Locator
  readonly threadList: Locator
  readonly refreshBtn: Locator

  constructor(page: Page) {
    this.page = page
    this.newThreadBtn = page.getByRole('button', { name: /new thread/i })
    this.healthBtn = page.getByRole('button', { name: /check health/i })
    this.logoutBtn = page.getByTitle('Sign out')
    this.obsToggle = page.getByText(/show observability|hide observability/i)
    this.threadList = page.locator('[class*="space-y-0.5"] > div, .space-y-0\\.5 > div')
    this.refreshBtn = page.getByTitle('Refresh')
  }

  async createNewThread() {
    await this.newThreadBtn.click()
  }

  async clickThread(index = 0) {
    await this.threadList.nth(index).click()
  }

  async checkHealth() {
    await this.healthBtn.click()
  }

  async toggleObservability() {
    await this.obsToggle.click()
  }

  async logout() {
    await this.logoutBtn.click()
  }
}

// ── ChatPanel ─────────────────────────────────────────────────────────────────

export class ChatPanelPOM {
  readonly page: Page
  readonly textarea: Locator
  readonly sendBtn: Locator
  readonly messages: Locator
  readonly loadingDots: Locator
  readonly budgetToggle: Locator
  readonly budgetInput: Locator
  readonly emptyState: Locator

  constructor(page: Page) {
    this.page = page
    this.textarea = page.getByPlaceholder(/ask a research question/i)
    this.sendBtn = page.getByRole('button', { name: /send/i })
    this.messages = page.locator('[class*="justify-end"], [class*="justify-start"]').filter({ hasText: /.+/ })
    this.loadingDots = page.locator('[class*="animate-bounce"]').first()
    this.budgetToggle = page.getByTitle('Budget settings')
    this.budgetInput = page.locator('input[type="number"]')
    this.emptyState = page.getByText(/no messages yet/i)
  }

  async typeMessage(text: string) {
    await this.textarea.fill(text)
  }

  async send() {
    await this.sendBtn.click()
  }

  async sendMessage(text: string) {
    await this.typeMessage(text)
    await this.send()
  }

  async sendWithCtrlEnter(text: string) {
    await this.typeMessage(text)
    await this.textarea.press('Control+Enter')
  }

  async waitForResponse(timeout = 30_000) {
    // Wait for loading dots to appear then disappear
    await this.loadingDots.waitFor({ state: 'visible', timeout: 5_000 }).catch(() => {})
    await this.loadingDots.waitFor({ state: 'hidden', timeout })
  }

  async getLastMessage() {
    const all = await this.messages.all()
    return all[all.length - 1]
  }
}
