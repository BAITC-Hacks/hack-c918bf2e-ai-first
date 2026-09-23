import type { Analysis, AnalysisCreated, CreateAnalysisInput } from './types'
import { createMockAnalysis, getMockAnalysis, isMockId } from './mock'

const REQUEST_TIMEOUT_MS = 20_000
const UPLOAD_TIMEOUT_MS = 120_000

export class ApiError extends Error {
  constructor(
    message: string,
    readonly kind: 'network' | 'timeout' | 'http',
    readonly status?: number,
  ) {
    super(message)
  }
}

export function apiBase(): string {
  const base = window.__APP_CONFIG__?.API_BASE ?? ''
  return base.replace(/\/+$/, '')
}

async function request<T>(path: string, init: RequestInit, timeoutMs: number): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  let response: Response
  try {
    response = await fetch(`${apiBase()}${path}`, { ...init, signal: controller.signal })
  } catch (error) {
    if (controller.signal.aborted) {
      throw new ApiError('Сервер не ответил вовремя', 'timeout')
    }
    throw new ApiError('Сервер анализа недоступен', 'network')
  } finally {
    window.clearTimeout(timer)
  }
  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      // Body is not JSON; keep the status text.
    }
    throw new ApiError(detail, 'http', response.status)
  }
  return (await response.json()) as T
}

export function createAnalysis(input: CreateAnalysisInput, useMock = false): Promise<AnalysisCreated> {
  if (useMock) return Promise.resolve(createMockAnalysis(input))
  const form = new FormData()
  input.beforeFiles.forEach((file) => form.append('before_files', file))
  input.afterFiles.forEach((file) => form.append('after_files', file))
  if (input.title?.trim()) form.append('title', input.title.trim())
  return request<AnalysisCreated>('/api/v1/analyses', { method: 'POST', body: form }, UPLOAD_TIMEOUT_MS)
}

export function getAnalysis(id: string): Promise<Analysis> {
  if (isMockId(id)) return Promise.resolve(getMockAnalysis(id))
  return request<Analysis>(`/api/v1/analyses/${encodeURIComponent(id)}`, { method: 'GET' }, REQUEST_TIMEOUT_MS)
}
