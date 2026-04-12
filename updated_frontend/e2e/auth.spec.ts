/**
 * E2E: Authentication flows
 * Covers: login success/failure, register success/failure, logout,
 *         auth-guard redirect, OAuth link presence
 *
 * Runs in the 'unauth' project (no stored auth state).
 */
import { test, expect } from '@playwright/test'
import { LoginPage, RegisterPage } from './pages/index'
import {
  mockLoginSuccess, mockLoginFailure,
  mockRegisterSuccess, mockRegisterFailure,
  mockThreadsEmpty, mockHealthOk,
} from './utils/mocks'

// ── Auth guard ────────────────────────────────────────────────────────────────

test.describe('Auth Guard', () => {
  test('unauthenticated user is redirected to /login from /', async ({ page }) => {
    await page.goto('/')
    await page.waitForURL(/\/login/, { timeout: 8_000 })
    await expect(page).toHaveURL(/\/login/)
  })

  test('login page renders correctly', async ({ page }) => {
    const lp = new LoginPage(page)
    await lp.goto()
    await expect(lp.emailInput).toBeVisible()
    await expect(lp.passwordInput).toBeVisible()
    await expect(lp.submitBtn).toBeVisible()
    await expect(lp.registerLink).toBeVisible()
  })

  test('register page renders correctly', async ({ page }) => {
    const rp = new RegisterPage(page)
    await rp.goto()
    await expect(rp.emailInput).toBeVisible()
    await expect(rp.usernameInput).toBeVisible()
    await expect(rp.passwordInput).toBeVisible()
    await expect(rp.submitBtn).toBeVisible()
    await expect(rp.loginLink).toBeVisible()
  })
})

// ── Login ─────────────────────────────────────────────────────────────────────

test.describe('Login', () => {
  test('successful login redirects to /', async ({ page }) => {
    await mockLoginSuccess(page)
    await mockThreadsEmpty(page)
    await mockHealthOk(page)

    const lp = new LoginPage(page)
    await lp.goto()
    await lp.login('user@test.com', 'password123')
    await page.waitForURL('/', { timeout: 10_000 })
    await expect(page).toHaveURL('/')
  })

  test('failed login shows error message', async ({ page }) => {
    await mockLoginFailure(page, 'Invalid credentials')
    const lp = new LoginPage(page)
    await lp.goto()
    await lp.login('bad@test.com', 'wrongpass')
    await lp.expectError('Invalid credentials')
    await expect(page).toHaveURL(/\/login/)
  })

  test('login button is disabled while loading', async ({ page }) => {
    // Delay the response to observe loading state
    await page.route('**/auth/login', async (route) => {
      await new Promise((r) => setTimeout(r, 500))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access_token: 'h.e.sig', refresh_token: 'r', token_type: 'bearer' }),
      })
    })
    const lp = new LoginPage(page)
    await lp.goto()
    await lp.emailInput.fill('u@t.com')
    await lp.passwordInput.fill('pass')
    await lp.submitBtn.click()
    // Button should show loading state
    await expect(lp.submitBtn).toBeDisabled()
  })

  test('empty email shows browser validation', async ({ page }) => {
    const lp = new LoginPage(page)
    await lp.goto()
    await lp.passwordInput.fill('pass')
    await lp.submitBtn.click()
    // HTML5 required validation prevents submission
    await expect(page).toHaveURL(/\/login/)
  })

  test('OAuth buttons are present and link to correct providers', async ({ page }) => {
    const lp = new LoginPage(page)
    await lp.goto()
    await expect(lp.googleBtn).toBeVisible()
    await expect(lp.githubBtn).toBeVisible()
    const googleHref = await lp.googleBtn.getAttribute('href')
    const githubHref = await lp.githubBtn.getAttribute('href')
    expect(googleHref).toContain('google')
    expect(githubHref).toContain('github')
  })

  test('navigate to register from login page', async ({ page }) => {
    const lp = new LoginPage(page)
    await lp.goto()
    await lp.registerLink.click()
    await expect(page).toHaveURL(/\/register/)
  })
})

// ── Register ──────────────────────────────────────────────────────────────────

test.describe('Register', () => {
  test('successful registration redirects to /', async ({ page }) => {
    await mockRegisterSuccess(page)
    await mockLoginSuccess(page)
    await mockThreadsEmpty(page)

    const rp = new RegisterPage(page)
    await rp.goto()
    await rp.register('new@test.com', 'newuser', 'Password123!')
    await page.waitForURL('/', { timeout: 10_000 })
    await expect(page).toHaveURL('/')
  })

  test('duplicate email shows error', async ({ page }) => {
    await mockRegisterFailure(page, 'Email already registered')
    const rp = new RegisterPage(page)
    await rp.goto()
    await rp.register('dup@test.com', 'dupuser', 'Password123!')
    await expect(rp.errorMsg).toContainText('Email already registered')
  })

  test('password minLength=8 enforced by browser', async ({ page }) => {
    const rp = new RegisterPage(page)
    await rp.goto()
    await rp.emailInput.fill('a@b.com')
    await rp.usernameInput.fill('user')
    await rp.passwordInput.fill('short')
    await rp.submitBtn.click()
    await expect(page).toHaveURL(/\/register/)
  })

  test('navigate to login from register page', async ({ page }) => {
    const rp = new RegisterPage(page)
    await rp.goto()
    await rp.loginLink.click()
    await expect(page).toHaveURL(/\/login/)
  })
})

// ── OAuth callback ────────────────────────────────────────────────────────────

test.describe('OAuth callback', () => {
  test('missing tokens redirect to /login with error', async ({ page }) => {
    await page.goto('/auth/callback')
    await page.waitForURL(/\/login/, { timeout: 8_000 })
    await expect(page).toHaveURL(/oauth_failed/)
  })

  test('valid tokens in URL complete sign-in', async ({ page }) => {
    await mockThreadsEmpty(page)
    const header = Buffer.from(JSON.stringify({ alg: 'none' })).toString('base64url')
    const payload = Buffer.from(JSON.stringify({
      sub: 'oauth-uid', email: 'oauth@test.com', username: 'oauthuser', role: 'user', exp: 9999999999,
    })).toString('base64url')
    const fakeJwt = `${header}.${payload}.sig`

    await page.goto(`/auth/callback?access_token=${fakeJwt}&refresh_token=ref-tok`)
    await page.waitForURL('/', { timeout: 10_000 })
    await expect(page).toHaveURL('/')
  })
})
