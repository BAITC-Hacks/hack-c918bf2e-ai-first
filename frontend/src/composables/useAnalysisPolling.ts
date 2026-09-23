import { onBeforeUnmount, ref, watch, type Ref } from 'vue'
import { ApiError, getAnalysis } from '@/api/client'
import type { Analysis } from '@/api/types'

const POLL_INTERVAL_MS = 1500
const MAX_CONSECUTIVE_FAILURES = 3

export function useAnalysisPolling(id: Ref<string>) {
  const analysis = ref<Analysis | null>(null)
  const pollError = ref<string | null>(null)
  const loading = ref(true)
  let timer: number | undefined
  let failures = 0
  let generation = 0

  function stop() {
    if (timer !== undefined) window.clearTimeout(timer)
    timer = undefined
  }

  async function tick(gen: number) {
    try {
      const data = await getAnalysis(id.value)
      if (gen !== generation) return
      analysis.value = data
      pollError.value = null
      failures = 0
      loading.value = false
      if (data.status === 'completed' || data.status === 'failed') return
    } catch (error) {
      if (gen !== generation) return
      failures += 1
      const notFound = error instanceof ApiError && error.status === 404
      if (notFound || failures >= MAX_CONSECUTIVE_FAILURES) {
        loading.value = false
        pollError.value = notFound
          ? 'Анализ не найден. Возможно, сервер был перезапущен.'
          : `${error instanceof Error ? error.message : 'Ошибка связи с сервером'}. Опрос остановлен после ${MAX_CONSECUTIVE_FAILURES} попыток.`
        return
      }
    }
    timer = window.setTimeout(() => tick(gen), POLL_INTERVAL_MS)
  }

  function start() {
    stop()
    generation += 1
    failures = 0
    pollError.value = null
    loading.value = analysis.value === null
    void tick(generation)
  }

  watch(
    id,
    () => {
      analysis.value = null
      start()
    },
    { immediate: true },
  )
  onBeforeUnmount(() => {
    generation += 1
    stop()
  })

  return { analysis, pollError, loading, retry: start }
}
