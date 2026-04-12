/**
 * API mock helpers — intercept backend calls via page.route().
 * All mocks are scoped to a single test via the passed `page`.
 *
 * Usage:
 *   import { mockAuth, mockResearchStream, mockHealth } from '../utils/mocks'
 *   await mockAuth(page)
 *   await mockResearchStream(page, ['Hello ', 'world'])
 */
import { type Page } from '@playwright/test'

const GW = process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? 'http://localhost:8000'
const AUTH = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL ?? 'http://localhost:8007'

// ── Auth mocks ────────────────────────────────────────────────────────────────

/** Fake JWT with a real base64 payload (no signature). */
function fakeJwt(sub = 'uid-e2e', email = 'e2e@test.local', username = 'e2e_user') {
  const header = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url')
  const payload = Buffer.from(JSON.stringify({
    sub, email, username, role: 'user', exp: 9999999999,
  })).toString('base64url')
  return `${header}.${payload}.mock`
}

export async function mockLoginSuccess(page: Page) {
  await page.route(`${AUTH}/auth/login`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: fakeJwt(),
        refresh_token: 'mock-refresh',
        token_type: 'bearer',
      }),
    })
  )
}

export async function mockLoginFailure(page: Page, detail = 'Invalid credentials') {
  await page.route(`${AUTH}/auth/login`, (route) =>
    route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail }) })
  )
}

export async function mockRegisterSuccess(page: Page) {
  await page.route(`${AUTH}/auth/register`, (route) =>
    route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'uid-new', email: 'new@test.local', username: 'newuser', role: 'user', is_active: true,
      }),
    })
  )
}

export async function mockRegisterFailure(page: Page, detail = 'Email already registered') {
  await page.route(`${AUTH}/auth/register`, (route) =>
    route.fulfill({ status: 400, contentType: 'application/json', body: JSON.stringify({ detail }) })
  )
}

export async function mockRefreshSuccess(page: Page) {
  await page.route(`${AUTH}/auth/refresh`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access_token: fakeJwt(), refresh_token: 'new-refresh', token_type: 'bearer' }),
    })
  )
}

// ── Threads / conversations mocks ─────────────────────────────────────────────

export async function mockThreadsEmpty(page: Page) {
  await page.route(`${GW}/api/v1/conversations/threads`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
  )
}

export async function mockThreads(page: Page, threads: { id: string; title: string }[]) {
  const body = threads.map((t) => ({
    id: t.id, user_id: 'uid-e2e', title: t.title, created_at: new Date().toISOString(),
  }))
  await page.route(`${GW}/api/v1/conversations/threads`, (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  )
}

export async function mockMessages(page: Page, threadId: string, messages: { role: string; content: string }[] = []) {
  await page.route(`${GW}/api/v1/conversations/threads/${threadId}/messages*`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(messages.map((m, i) => ({
        id: `msg-${i}`, thread_id: threadId, role: m.role, content: m.content,
        created_at: new Date().toISOString(),
      }))),
    })
  )
}

export async function mockDeleteThread(page: Page) {
  await page.route(`${GW}/api/v1/conversations/threads/**`, (route) => {
    if (route.request().method() === 'DELETE') {
      route.fulfill({ status: 204, body: '' })
    } else {
      route.continue()
    }
  })
}

// ── Research stream mock ──────────────────────────────────────────────────────

/**
 * Mock the SSE research stream.
 * @param chunks  Array of text chunks to stream as tokens
 * @param mode    Research mode to report in the done event
 */
export async function mockResearchStream(
  page: Page,
  chunks: string[] = ['This is a ', 'mock response.'],
  mode = 'quick',
) {
  await page.route(`${GW}/api/v1/research/run/stream`, async (route) => {
    const events = [
      `data: ${JSON.stringify({ type: 'node_start', node: 'classify' })}\n\n`,
      `data: ${JSON.stringify({ type: 'node_end', node: 'classify' })}\n\n`,
      `data: ${JSON.stringify({ type: 'node_start', node: 'quick_mode' })}\n\n`,
      `data: ${JSON.stringify({ type: 'report_start' })}\n\n`,
      ...chunks.map((c) => `data: ${JSON.stringify({ type: 'token', chunk: c })}\n\n`),
      `data: ${JSON.stringify({ type: 'node_end', node: 'quick_mode' })}\n\n`,
      `data: ${JSON.stringify({ type: 'done', sources: ['https://example.com'], mode, iterations: 1, token_usage: 42 })}\n\n`,
      'data: [DONE]\n\n',
    ]
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' },
      body: events.join(''),
    })
  })
}

export async function mockResearchStreamError(page: Page, message = 'LLM timeout') {
  await page.route(`${GW}/api/v1/research/run/stream`, async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body: [
        `data: ${JSON.stringify({ type: 'error', message })}\n\n`,
        'data: [DONE]\n\n',
      ].join(''),
    })
  })
}

export async function mockResearchStreamGatewayError(page: Page) {
  await page.route(`${GW}/api/v1/research/run/stream`, (route) =>
    route.fulfill({ status: 502, body: 'Bad Gateway' })
  )
}

// ── Health mock ───────────────────────────────────────────────────────────────

export async function mockHealthOk(page: Page) {
  await page.route(`${GW}/api/v1/health/`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        overall: 'ok',
        services: {
          'intent-service': 'ok', 'memory-service': 'ok',
          'search-service': 'ok', 'synthesis-service': 'ok', 'research-service': 'ok',
        },
      }),
    })
  )
}

export async function mockHealthDegraded(page: Page) {
  await page.route(`${GW}/api/v1/health/`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        overall: 'degraded',
        services: { 'research-service': 'unreachable', 'intent-service': 'ok' },
      }),
    })
  )
}
