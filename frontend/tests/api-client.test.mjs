import assert from 'node:assert/strict'
import { afterEach, beforeEach, test } from 'node:test'
import { loadModule } from './helpers.mjs'

const { ApiError, apiBase, getAnalysis, createAnalysis } = await loadModule('src/api/client.ts')
const originalFetch = globalThis.fetch
const originalWindow = globalThis.window
const analysis = { id: 'real-id', status: 'completed', findings: [] }

beforeEach(() => {
  globalThis.window = { setTimeout, clearTimeout }
  globalThis.fetch = async () => Response.json(analysis)
})
afterEach(() => {
  globalThis.fetch = originalFetch
  if (originalWindow === undefined) delete globalThis.window
  else globalThis.window = originalWindow
})

test('unavailable config uses the same-origin API and returns real results', async () => {
  globalThis.fetch = async (url) => {
    assert.equal(url, '/api/v1/analyses/real-id')
    return Response.json(analysis)
  }
  assert.equal(apiBase(), '')
  assert.deepEqual(await getAnalysis('real-id'), analysis)
})

test('explicitly empty runtime config also selects the same-origin proxy', () => {
  window.__APP_CONFIG__ = { API_BASE: '' }
  assert.equal(apiBase(), '')
  window.__APP_CONFIG__ = {}
  assert.equal(apiBase(), '')
})

test('an explicit external API origin still works without rebuilding', async () => {
  window.__APP_CONFIG__ = { API_BASE: ' https://api.example.test/// ' }
  globalThis.fetch = async (url) => {
    assert.equal(url, 'https://api.example.test/api/v1/analyses/real-id')
    return Response.json(analysis)
  }
  assert.deepEqual(await getAnalysis('real-id'), analysis)
})

test('real uploads use multipart through the same-origin API, never a demo fallback', async () => {
  globalThis.fetch = async (url, init) => {
    assert.equal(url, '/api/v1/analyses')
    assert.equal(init.method, 'POST')
    assert.ok(init.body instanceof FormData)
    assert.equal(init.body.get('before_files').name, 'before.docx')
    assert.equal(init.body.get('after_files').name, 'after.docx')
    assert.equal(init.body.get('title'), 'Test')
    assert.equal(init.headers, undefined, 'fetch must choose the multipart boundary')
    return Response.json({ id: 'real-created', status: 'queued' }, { status: 202 })
  }
  const result = await createAnalysis({ title: ' Test ',
    beforeFiles: [new File(['before'], 'before.docx')],
    afterFiles: [new File(['after'], 'after.docx')],
  })
  assert.equal(result.id, 'real-created')
})

test('HTML with HTTP 200 produces a useful configuration error, not parser internals', async () => {
  globalThis.fetch = async () => new Response('<!doctype html><title>SPA</title>', {
    headers: { 'Content-Type': 'text/html' },
  })
  await assert.rejects(getAnalysis('real-id'), error => {
    assert.ok(error instanceof ApiError)
    assert.equal(error.kind, 'response')
    assert.match(error.message, /не JSON.*проксирования \/api/)
    assert.doesNotMatch(error.message, /doctype|Unexpected token/)
    return true
  })
})

test('malformed JSON has a separate recoverable response error', async () => {
  globalThis.fetch = async () => new Response('{broken', { headers: { 'Content-Type': 'application/json' } })
  await assert.rejects(getAnalysis('real-id'), error => error.kind === 'response' && /некорректный JSON/.test(error.message))
})

test('JSON HTTP errors preserve the status for the not-found screen', async () => {
  globalThis.fetch = async () => Response.json({ detail: 'Анализ не найден' }, { status: 404 })
  await assert.rejects(getAnalysis('real-id'), error =>
    error.kind === 'http' && error.status === 404 && error.message === 'Анализ не найден')
})

test('upstream HTML error preserves HTTP status without exposing response content', async () => {
  globalThis.fetch = async () => new Response('<html>internal upstream details</html>', { status: 502 })
  await assert.rejects(getAnalysis('real-id'), error =>
    error.kind === 'http' && error.status === 502 && error.message === 'Ошибка сервиса анализа (HTTP 502)')
})

test('network failures remain recoverable errors and never turn into demo data', async () => {
  globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
  await assert.rejects(getAnalysis('real-id'), error => error.kind === 'network')
})

test('timeouts cover both headers and body, and clean up their timer', async () => {
  for (const phase of ['headers', 'body']) {
    let cleared = 0
    window.setTimeout = callback => setTimeout(callback, 10)
    window.clearTimeout = timer => { cleared += 1; clearTimeout(timer) }
    globalThis.fetch = async (_url, { signal }) => {
      const stalled = () => new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true })
      })
      if (phase === 'headers') return stalled()
      return { ok: true, status: 200, headers: new Headers({ 'content-type': 'application/json' }), json: stalled }
    }
    await assert.rejects(getAnalysis('real-id'), error => error.kind === 'timeout')
    assert.equal(cleared, 1, `${phase}: the timer must be cleared`)
  }
})
