/**
 * Frontend Observability — mirrors the backend ServiceTracker pattern.
 *
 * 1. PREVENTION  — validate inputs before operations run
 * 2. DETECTION   — capture errors / slow calls as they happen
 * 3. AVOIDANCE   — warn before thresholds are breached (circuit-breaker style)
 * 4. RECTIFICATION — structured error records for post-mortem / retry
 */

export type Stage = 'prevention' | 'detection' | 'avoidance' | 'rectification'

export interface IssueRecord {
  stage: Stage
  service: string
  operation: string
  message: string
  context: Record<string, unknown>
  ts: string
  errorType?: string
  errorStack?: string
}

// ── In-memory ring buffer (last 200 issues) ──────────────────────────────────

const MAX_RECORDS = 200
const _records: IssueRecord[] = []
const _callCounts: Record<string, number> = {}
const _errorCounts: Record<string, number> = {}

function push(rec: IssueRecord) {
  if (_records.length >= MAX_RECORDS) _records.shift()
  _records.push(rec)
}

// ── Structured logger ─────────────────────────────────────────────────────────

const LOG_LEVEL = (process.env.NEXT_PUBLIC_LOG_LEVEL ?? 'info').toLowerCase()
const LEVELS = { debug: 0, info: 1, warn: 2, error: 3 }
const currentLevel = LEVELS[LOG_LEVEL as keyof typeof LEVELS] ?? 1

function log(level: 'debug' | 'info' | 'warn' | 'error', msg: string, ctx?: Record<string, unknown>) {
  if (LEVELS[level] < currentLevel) return
  // Trim errorStack to first 3 lines to keep logs readable
  const safeCtx = ctx ? trimStacks(ctx) : undefined
  const payload = { ts: new Date().toISOString(), level, service: 'frontend', msg, ...safeCtx }
  // eslint-disable-next-line no-console
  console[level](JSON.stringify(payload))
}

function trimStacks(obj: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(obj)) {
    if (k === 'errorStack' && typeof v === 'string') {
      out[k] = v.split('\n').slice(0, 3).join('\n')
    } else if (k === 'tracker' && v && typeof v === 'object') {
      out[k] = trimStacks(v as Record<string, unknown>)
    } else {
      out[k] = v
    }
  }
  return out
}

// ── 1. PREVENTION ─────────────────────────────────────────────────────────────

/**
 * Assert a precondition. Throws if condition is false and raiseOnFail=true.
 * Returns true/false otherwise.
 */
export function prevent(
  rule: string,
  condition: boolean,
  context: Record<string, unknown> = {},
  raiseOnFail = true,
): boolean {
  if (condition) return true
  const rec: IssueRecord = {
    stage: 'prevention',
    service: 'frontend',
    operation: rule,
    message: `Prevention rule FAILED: ${rule}`,
    context,
    ts: new Date().toISOString(),
  }
  push(rec)
  log('warn', rec.message, { tracker: rec })
  if (raiseOnFail) throw new Error(`[frontend] Prevention failed: ${rule}`)
  return false
}

// ── 2. DETECTION ──────────────────────────────────────────────────────────────

/**
 * Wrap an async operation with latency tracking and error capture.
 * Logs a warning for slow calls (>3 s) and error for exceptions.
 */
export async function detect<T>(
  operation: string,
  fn: () => Promise<T>,
  context: Record<string, unknown> = {},
  swallowError = false,
): Promise<T | undefined> {
  _callCounts[operation] = (_callCounts[operation] ?? 0) + 1
  const start = performance.now()
  try {
    const result = await fn()
    const elapsed = (performance.now() - start) / 1000
    if (elapsed > 3) {
      const rec: IssueRecord = {
        stage: 'detection',
        service: 'frontend',
        operation,
        message: `Slow operation: ${operation} took ${elapsed.toFixed(2)}s`,
        context: { ...context, latency_s: +elapsed.toFixed(3) },
        ts: new Date().toISOString(),
      }
      push(rec)
      log('warn', rec.message, { tracker: rec })
    } else {
      log('debug', `Operation OK: ${operation} (${elapsed.toFixed(3)}s)`, { latency_s: elapsed })
    }
    return result
  } catch (err) {
    const elapsed = (performance.now() - start) / 1000
    _errorCounts[operation] = (_errorCounts[operation] ?? 0) + 1
    const error = err instanceof Error ? err : new Error(String(err))
    const rec: IssueRecord = {
      stage: 'detection',
      service: 'frontend',
      operation,
      message: `Exception in ${operation}: ${error.message}`,
      context: { ...context, latency_s: +elapsed.toFixed(3) },
      ts: new Date().toISOString(),
      errorType: error.name,
      errorStack: error.stack,
    }
    push(rec)
    log('error', rec.message, { tracker: rec })
    // swallowError=true: record but don't re-throw — caller handles absence of return value
    if (swallowError) return undefined
    throw err
  }
}

// ── 3. AVOIDANCE ──────────────────────────────────────────────────────────────

/**
 * Emit a warning when a metric approaches a dangerous threshold.
 * Does NOT throw — it's a proactive signal.
 */
export function avoid(
  metric: string,
  current: number,
  threshold: number,
  context: Record<string, unknown> = {},
): void {
  if (current < threshold) return
  const rec: IssueRecord = {
    stage: 'avoidance',
    service: 'frontend',
    operation: metric,
    message: `Avoidance alert: ${metric} = ${current.toFixed(3)} exceeds threshold ${threshold.toFixed(3)}`,
    context: { ...context, current, threshold },
    ts: new Date().toISOString(),
  }
  push(rec)
  log('warn', rec.message, { tracker: rec })
}

/** Convenience: compute error rate for an operation and call avoid(). */
export function checkErrorRate(operation: string, threshold = 0.3): void {
  const calls = _callCounts[operation] ?? 0
  const errors = _errorCounts[operation] ?? 0
  if (calls === 0) return
  avoid(`${operation}_error_rate`, errors / calls, threshold, { calls, errors })
}

// ── 4. RECTIFICATION ─────────────────────────────────────────────────────────

/**
 * Record a structured error with full context for post-mortem / retry logic.
 * Returns the IssueRecord so callers can attach it to UI state.
 */
export function rectify(
  err: unknown,
  operation: string,
  context: Record<string, unknown> = {},
  reraise = false,
): IssueRecord {
  const error = err instanceof Error ? err : new Error(String(err))
  const rec: IssueRecord = {
    stage: 'rectification',
    service: 'frontend',
    operation,
    message: `Rectification needed for ${operation}: ${error.message}`,
    context,
    ts: new Date().toISOString(),
    errorType: error.name,
    errorStack: error.stack,
  }
  push(rec)
  log('error', rec.message, { tracker: rec })
  if (reraise) throw err
  return rec
}

// ── Inspection ────────────────────────────────────────────────────────────────

export function recentIssues(stage?: Stage, limit = 50): IssueRecord[] {
  const filtered = stage ? _records.filter((r) => r.stage === stage) : _records
  return filtered.slice(-limit)
}

export function stats(): Record<string, { calls: number; errors: number; error_rate: number }> {
  return Object.fromEntries(
    Object.keys(_callCounts).map((op) => [
      op,
      {
        calls: _callCounts[op],
        errors: _errorCounts[op] ?? 0,
        error_rate: _callCounts[op] ? +(((_errorCounts[op] ?? 0) / _callCounts[op]).toFixed(3)) : 0,
      },
    ])
  )
}
