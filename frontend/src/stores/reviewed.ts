// "Отметить как проверенное" is local-only (handoff §10): nothing is sent to the backend.
import { reactive } from 'vue'

const KEY = 'sverka-reviewed'
const marks = reactive(new Set<string>())

try {
  const saved = JSON.parse(localStorage.getItem(KEY) ?? '[]')
  if (Array.isArray(saved)) saved.forEach((k) => typeof k === 'string' && marks.add(k))
} catch {
  // Storage unavailable or corrupted: start empty.
}

const key = (analysisId: string, findingId: string) => `${analysisId}:${findingId}`

export function isReviewed(analysisId: string, findingId: string): boolean {
  return marks.has(key(analysisId, findingId))
}

export function toggleReviewed(analysisId: string, findingId: string) {
  const k = key(analysisId, findingId)
  if (marks.has(k)) marks.delete(k)
  else marks.add(k)
  try {
    localStorage.setItem(KEY, JSON.stringify([...marks]))
  } catch {
    // Ignore: the mark lives for this session only.
  }
}
