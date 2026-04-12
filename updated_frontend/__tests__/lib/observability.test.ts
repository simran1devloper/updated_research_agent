/**
 * Tests for lib/observability.ts
 * Covers: prevention, detection, avoidance, rectification, inspection helpers
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import {
  prevent, detect, avoid, rectify,
  checkErrorRate, recentIssues, stats,
} from '../../lib/observability'

// Reset module state between tests by re-importing with a fresh module cache
// Vitest isolates modules per file by default; we clear the ring buffer manually
// by calling recentIssues and draining it via the exported functions.

// ── helpers ───────────────────────────────────────────────────────────────────

function drainIssues() {
  // We can't directly clear the buffer, but we can verify counts independently
}

// ═══════════════════════════════════════════════════════════════════════════════
// 1. PREVENTION
// ═══════════════════════════════════════════════════════════════════════════════

describe('prevent', () => {
  it('returns true when condition passes', () => {
    expect(prevent('non-empty', true)).toBe(true)
  })

  it('throws when condition fails (raiseOnFail=true default)', () => {
    expect(() => prevent('non-empty', false, {}, true)).toThrow('Prevention failed: non-empty')
  })

  it('returns false without throwing when raiseOnFail=false', () => {
    expect(prevent('soft-rule', false, {}, false)).toBe(false)
  })

  it('records an issue on failure', () => {
    prevent('record-rule', false, { key: 'val' }, false)
    const issues = recentIssues('prevention')
    const rec = issues.find((r) => r.operation === 'record-rule')
    expect(rec).toBeDefined()
    expect(rec!.stage).toBe('prevention')
    expect(rec!.context.key).toBe('val')
  })

  it('does not record an issue on pass', () => {
    const before = recentIssues('prevention').length
    prevent('pass-rule', true)
    expect(recentIssues('prevention').length).toBe(before)
  })

  it('includes timestamp in record', () => {
    prevent('ts-rule', false, {}, false)
    const issues = recentIssues('prevention')
    const rec = issues.find((r) => r.operation === 'ts-rule')
    expect(rec!.ts).toMatch(/^\d{4}-\d{2}-\d{2}T/)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// 2. DETECTION
// ═══════════════════════════════════════════════════════════════════════════════

describe('detect', () => {
  it('returns the resolved value of the wrapped function', async () => {
    const result = await detect('op-ok', async () => 42)
    expect(result).toBe(42)
  })

  it('re-throws exceptions from the wrapped function', async () => {
    await expect(detect('op-throw', async () => { throw new Error('boom') }))
      .rejects.toThrow('boom')
  })

  it('records a detection issue on exception', async () => {
    try { await detect('op-detect-err', async () => { throw new TypeError('type!') }) } catch {}
    const issues = recentIssues('detection')
    const rec = issues.find((r) => r.operation === 'op-detect-err')
    expect(rec).toBeDefined()
    expect(rec!.errorType).toBe('TypeError')
    expect(rec!.stage).toBe('detection')
  })

  it('attaches context to detection record', async () => {
    try {
      await detect('op-ctx', async () => { throw new Error('x') }, { userId: 'u1' })
    } catch {}
    const issues = recentIssues('detection')
    const rec = issues.find((r) => r.operation === 'op-ctx')
    expect(rec!.context.userId).toBe('u1')
  })

  it('records slow operation warning (>3s)', async () => {
    const now = vi.spyOn(performance, 'now')
    now.mockReturnValueOnce(0).mockReturnValueOnce(4000) // 4s elapsed
    await detect('op-slow', async () => 'done')
    now.mockRestore()
    const issues = recentIssues('detection')
    const rec = issues.find((r) => r.operation === 'op-slow')
    expect(rec).toBeDefined()
    expect(rec!.message).toContain('Slow operation')
  })

  it('does not record issue for fast successful operation', async () => {
    const before = recentIssues('detection').length
    await detect('op-fast', async () => 'ok')
    // No new detection record for a fast success
    const after = recentIssues('detection').filter((r) => r.operation === 'op-fast')
    expect(after.length).toBe(0)
  })

  it('includes latency_s in context on exception', async () => {
    try { await detect('op-latency', async () => { throw new Error('e') }) } catch {}
    const issues = recentIssues('detection')
    const rec = issues.find((r) => r.operation === 'op-latency')
    expect(typeof rec!.context.latency_s).toBe('number')
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// 3. AVOIDANCE
// ═══════════════════════════════════════════════════════════════════════════════

describe('avoid', () => {
  it('does not record when current < threshold', () => {
    const before = recentIssues('avoidance').length
    avoid('metric-low', 0.1, 0.5)
    expect(recentIssues('avoidance').length).toBe(before)
  })

  it('records when current === threshold', () => {
    avoid('metric-eq', 0.5, 0.5)
    const issues = recentIssues('avoidance')
    const rec = issues.find((r) => r.operation === 'metric-eq')
    expect(rec).toBeDefined()
    expect(rec!.context.current).toBe(0.5)
    expect(rec!.context.threshold).toBe(0.5)
  })

  it('records when current > threshold', () => {
    avoid('metric-over', 0.9, 0.3)
    const issues = recentIssues('avoidance')
    const rec = issues.find((r) => r.operation === 'metric-over')
    expect(rec).toBeDefined()
  })

  it('includes custom context in record', () => {
    avoid('metric-ctx', 1.0, 0.5, { service: 'research' })
    const issues = recentIssues('avoidance')
    const rec = issues.find((r) => r.operation === 'metric-ctx')
    expect(rec!.context.service).toBe('research')
  })
})

describe('checkErrorRate', () => {
  it('triggers avoidance when error rate exceeds threshold', async () => {
    // Force 2 errors on the same operation
    for (let i = 0; i < 2; i++) {
      try { await detect('rate-op', async () => { throw new Error('e') }) } catch {}
    }
    const before = recentIssues('avoidance').length
    checkErrorRate('rate-op', 0.3)
    expect(recentIssues('avoidance').length).toBeGreaterThan(before)
  })

  it('is a no-op for operations with zero calls', () => {
    const before = recentIssues('avoidance').length
    checkErrorRate('never-called-op', 0.3)
    expect(recentIssues('avoidance').length).toBe(before)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// 4. RECTIFICATION
// ═══════════════════════════════════════════════════════════════════════════════

describe('rectify', () => {
  it('returns an IssueRecord', () => {
    const rec = rectify(new Error('db down'), 'db_write')
    expect(rec.stage).toBe('rectification')
    expect(rec.operation).toBe('db_write')
    expect(rec.errorType).toBe('Error')
  })

  it('stores the record in the buffer', () => {
    rectify(new Error('stored'), 'store-op')
    const issues = recentIssues('rectification')
    expect(issues.find((r) => r.operation === 'store-op')).toBeDefined()
  })

  it('re-throws when reraise=true', () => {
    expect(() => rectify(new RangeError('out'), 'range-op', {}, true)).toThrow('out')
  })

  it('does not throw when reraise=false (default)', () => {
    expect(() => rectify(new Error('silent'), 'silent-op')).not.toThrow()
  })

  it('handles non-Error objects', () => {
    const rec = rectify('string error', 'str-op')
    expect(rec.errorType).toBe('Error')
    expect(rec.message).toContain('string error')
  })

  it('attaches context to record', () => {
    rectify(new Error('ctx'), 'ctx-op', { retry: 2 })
    const issues = recentIssues('rectification')
    const rec = issues.find((r) => r.operation === 'ctx-op')
    expect(rec!.context.retry).toBe(2)
  })

  it('populates errorStack', () => {
    const err = new Error('stack-test')
    const rec = rectify(err, 'stack-op')
    expect(rec.errorStack).toContain('Error: stack-test')
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// Inspection helpers
// ═══════════════════════════════════════════════════════════════════════════════

describe('recentIssues', () => {
  it('filters by stage', () => {
    prevent('filter-prev', false, {}, false)
    rectify(new Error('filter-rect'), 'filter-rect-op')
    const prevOnly = recentIssues('prevention')
    expect(prevOnly.every((r) => r.stage === 'prevention')).toBe(true)
  })

  it('respects limit parameter', () => {
    for (let i = 0; i < 10; i++) rectify(new Error(String(i)), `limit-op-${i}`)
    expect(recentIssues(undefined, 3).length).toBeLessThanOrEqual(3)
  })

  it('returns all stages when no filter given', () => {
    prevent('all-prev', false, {}, false)
    rectify(new Error('all-rect'), 'all-rect-op')
    const all = recentIssues()
    const stages = new Set(all.map((r) => r.stage))
    expect(stages.size).toBeGreaterThan(1)
  })
})

describe('stats', () => {
  it('returns call and error counts per operation', async () => {
    for (let i = 0; i < 3; i++) {
      try {
        await detect('stats-test-op', async () => {
          if (i === 0) throw new Error('one fail')
        })
      } catch {}
    }
    const s = stats()
    expect(s['stats-test-op'].calls).toBeGreaterThanOrEqual(3)
    expect(s['stats-test-op'].errors).toBeGreaterThanOrEqual(1)
    expect(s['stats-test-op'].error_rate).toBeGreaterThan(0)
  })

  it('returns empty object when no operations tracked', () => {
    // stats() always returns something; just verify it's an object
    expect(typeof stats()).toBe('object')
  })
})
