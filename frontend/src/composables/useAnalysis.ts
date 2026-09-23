// One polled analysis per id, shared by the run / overview / conclusion routes so
// switching tabs never refetches or restarts polling.
import { ref, shallowRef, type Ref } from 'vue'
import { ApiError, getAnalysis } from '@/api/client'
import type { Analysis } from '@/api/types'

const POLL_INTERVAL_MS = 1500
const MAX_CONSECUTIVE_FAILURES = 3

export interface AnalysisHandle {
  analysis: Ref<Analysis | null>
  pollError: Ref<string | null>
  /** 'not_found' — the server does not know this id; 'unavailable' — no answer / HTTP error. */
  pollErrorKind: Ref<'not_found' | 'unavailable' | null>
  /** Wall-clock run time, known only when this tab watched the run finish. */
  durationMs: Ref<number | null>
  retry: () => void
  stop: () => void
}

export const crumbTitle = ref('')

const cache = new Map<string, AnalysisHandle>()

export function useAnalysis(id: string): AnalysisHandle {
  const existing = cache.get(id)
  if (existing) {
    if (existing.analysis.value) crumbTitle.value = existing.analysis.value.title ?? ''
    return existing
  }

  const analysis = shallowRef<Analysis | null>(null)
  const pollError = ref<string | null>(null)
  const pollErrorKind = ref<'not_found' | 'unavailable' | null>(null)
  const durationMs = ref<number | null>(null)
  let timer: number | undefined
  let failures = 0
  let generation = 0
  let sawRunning = false

  async function tick(gen: number) {
    try {
      const data = await getAnalysis(id)
      if (gen !== generation) return
      analysis.value = data
      crumbTitle.value = data.title ?? ''
      pollError.value = null
      pollErrorKind.value = null
      failures = 0
      const active = data.status === 'queued' || data.status === 'processing'
      if (active) sawRunning = true
      if (!active) {
        if (sawRunning && data.status === 'completed' && data.created_at) {
          durationMs.value = Date.now() - Date.parse(data.created_at)
        }
        return
      }
    } catch (error) {
      if (gen !== generation) return
      failures += 1
      const notFound = error instanceof ApiError && error.status === 404
      if (notFound || failures >= MAX_CONSECUTIVE_FAILURES) {
        pollErrorKind.value = notFound ? 'not_found' : 'unavailable'
        pollError.value = notFound
          ? 'Сервер не знает анализ с таким идентификатором: ссылка неверна или результат не сохранился. Загрузите документы и запустите анализ заново.'
          : `${error instanceof Error ? error.message : 'Нет связи с сервисом'}. Опрос остановлен после ${MAX_CONSECUTIVE_FAILURES} попыток.`
        return
      }
    }
    timer = window.setTimeout(() => void tick(gen), POLL_INTERVAL_MS)
  }

  function stop() {
    generation += 1
    if (timer !== undefined) window.clearTimeout(timer)
    timer = undefined
  }

  function retry() {
    stop()
    failures = 0
    pollError.value = null
    pollErrorKind.value = null
    void tick(generation)
  }

  const handle: AnalysisHandle = { analysis, pollError, pollErrorKind, durationMs, retry, stop }
  cache.set(id, handle)
  crumbTitle.value = ''
  retry()
  return handle
}
