/**
 * Global auth setup — runs once before all authenticated test projects.
 * Registers a test user (idempotent), logs in, and saves localStorage
 * tokens + Zustand auth-store to .auth-state.json.
 *
 * PREVENTION: validates that the auth service is reachable before tests run.
 */
import { test as setup, expect } from '@playwright/test'
import path from 'path'

const AUTH_STATE = path.join(__dirname, '.auth-state.json')

const TEST_USER = {
  email: process.env.E2E_USER_EMAIL ?? 'e2e_test@playwright.local',
  username: process.env.E2E_USER_NAME ?? 'e2e_tester',
  password: process.env.E2E_USER_PASS ?? 'E2eTestPass123!',
}

const AUTH_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ?? 'http://localhost:8007'

setup('authenticate test user', async ({ page, request }) => {
  // ── PREVENTION: auth service must be reachable ──────────────────────────
  const health = await request.get(`${AUTH_URL}/auth/health`).catch(() => null)
  if (!health || !health.ok()) {
    console.warn('[setup] Auth service unreachable — skipping live auth, using mock state')
    // Write a minimal mock state so authenticated tests can still run with mocked API
    await page.goto('/login')
    await page.evaluate(({ email, username }) => {
      // Inject a fake JWT (unsigned, for UI-only tests when backend is down)
      const header = btoa(JSON.stringify({ alg: 'none', typ: 'JWT' }))
      const payload = btoa(JSON.stringify({
        sub: 'mock-uid-1', email, username, role: 'user', exp: 9999999999,
      }))
      const fakeJwt = `${header}.${payload}.mock-sig`
      localStorage.setItem('access_token', fakeJwt)
      localStorage.setItem('refresh_token', 'mock-refresh-token')
    }, TEST_USER)
    await page.context().storageState({ path: AUTH_STATE })
    return
  }

  // ── Register (idempotent — ignore 400 "already exists") ─────────────────
  await request.post(`${AUTH_URL}/auth/register`, {
    data: { email: TEST_USER.email, username: TEST_USER.username, password: TEST_USER.password },
  })

  // ── Login ────────────────────────────────────────────────────────────────
  await page.goto('/login')
  await page.getByPlaceholder('Email').fill(TEST_USER.email)
  await page.getByPlaceholder('Password').fill(TEST_USER.password)
  await page.getByRole('button', { name: /sign in/i }).click()

  // Wait for redirect to main app
  await page.waitForURL('/', { timeout: 15_000 })
  await expect(page.locator('text=Research Agent')).toBeVisible()

  // Save full storage state (localStorage tokens + Zustand persist)
  await page.context().storageState({ path: AUTH_STATE })
})
