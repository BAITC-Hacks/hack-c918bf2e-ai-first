import type { Analysis, AnalysisCreated, CreateAnalysisInput } from './types'
import { createMockAnalysis, getMockAnalysis, isMockId } from './mock'

const REQUEST_TIMEOUT_MS = 20_000
const UPLOAD_TIMEOUT_MS = 180_000

export class ApiError extends Error {
  constructor(
    message: string,
    readonly kind: 'network' | 'timeout' | 'http' | 'response',
    readonly status?: number,
  ) {
    super(message)
  }
}

export function apiBase(): string {
  // Empty or unavailable config means the same-origin /api proxy, never mock data.
  return (window.__APP_CONFIG__?.API_BASE ?? '').trim().replace(/\/+$/, '')
}

async function request<T>(path: string, init: RequestInit, timeoutMs: number): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(`${apiBase()}${path}`, { ...init, signal: controller.signal })
    if (!response.ok) {
      let detail = `Ошибка сервиса анализа (HTTP ${response.status})`
      try {
        const body = await response.json()
        if (typeof body?.detail === 'string') detail = body.detail
      } catch {
        // Do not show nginx HTML or parser internals in a user-facing error.
      }
      throw new ApiError(detail, 'http', response.status)
    }
    const contentType = response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() ?? ''
    if (contentType !== 'application/json' && !contentType.endsWith('+json')) {
      throw new ApiError(
        'Сервис анализа вернул не JSON. Проверьте адрес API и настройку проксирования /api в nginx',
        'response', response.status,
      )
    }
    try {
      return (await response.json()) as T
    } catch {
      throw new ApiError('Сервис анализа вернул некорректный JSON. Повторите запрос', 'response', response.status)
    }
  } catch (error) {
    if (controller.signal.aborted) throw new ApiError('Сервер не ответил вовремя', 'timeout')
    if (error instanceof ApiError) throw error
    throw new ApiError('Сервис анализа недоступен', 'network')
  } finally {
    // Keep the timeout active until the body is read, not just until headers arrive.
    window.clearTimeout(timer)
  }
}

export function createAnalysis(input: CreateAnalysisInput, useMock = false): Promise<AnalysisCreated> {
  if (useMock) return Promise.resolve(createMockAnalysis(input.title))
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
