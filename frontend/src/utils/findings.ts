import type { Evidence, Finding } from '@/api/types'
import { SEVERITY_META, TYPE_ORDER } from './labels'

export type SortKey = 'priority' | 'confidence' | 'department'

export function department(f: Finding): string {
  return f.after?.department ?? f.before?.department ?? '—'
}

/**
 * Clause locators are strings («3.4», «абзац 12», «таблица 2, строка 3», «Лист1!7»):
 * only a printed number gets the «п.» prefix, nothing is parsed or renumbered.
 */
export function locatorLabel(clause: string): string {
  return /^\d/.test(clause.trim()) ? `п. ${clause.trim()}` : clause.trim()
}

export function clauseLabel(e: Evidence | null | undefined): string {
  if (!e) return '—'
  const parts = [e.clause ? locatorLabel(e.clause) : null, e.page ? `стр. ${e.page}` : null].filter(Boolean)
  return parts.length ? parts.join(' · ') : 'пункт не указан'
}

export function primaryEvidence(f: Finding): Evidence | null {
  return f.before ?? f.after
}

const byPriority = (a: Finding, b: Finding) =>
  SEVERITY_META[a.severity].rank - SEVERITY_META[b.severity].rank ||
  TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type) ||
  b.confidence - a.confidence

export function sortFindings(list: Finding[], key: SortKey): Finding[] {
  const copy = [...list]
  if (key === 'confidence') return copy.sort((a, b) => b.confidence - a.confidence || byPriority(a, b))
  if (key === 'department') return copy.sort((a, b) => department(a).localeCompare(department(b), 'ru') || byPriority(a, b))
  return copy.sort(byPriority)
}

export function isQcWarning(message: string): boolean {
  return /контрол\S*\s+качеств/i.test(message)
}

/** Plain-text citation used by "Копировать цитату со ссылкой". */
export function citation(e: Evidence): string {
  const where = [e.document, e.clause ? locatorLabel(e.clause) : null, e.page ? `стр. ${e.page}` : null].filter(Boolean).join(', ')
  return `«${e.quote}» — ${where}${e.department ? ` (${e.department})` : ''}`
}

export interface DiffSegment {
  text: string
  kind: 'same' | 'del' | 'add'
}

/** Word-level LCS diff: returns segments for the "before" and "after" quotes. */
export function wordDiff(before: string, after: string): { before: DiffSegment[]; after: DiffSegment[] } {
  const a = before.split(/(\s+)/)
  const b = after.split(/(\s+)/)
  const norm = (w: string) => w.toLowerCase().replace(/[«»".,;:()]/g, '')
  const n = a.length
  const m = b.length
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0))
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      dp[i][j] = norm(a[i]) === norm(b[j]) ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])

  const left: DiffSegment[] = []
  const right: DiffSegment[] = []
  const push = (list: DiffSegment[], text: string, kind: DiffSegment['kind']) => {
    const last = list[list.length - 1]
    // Whitespace between two changed words stays inside the highlighted span.
    if (last && (last.kind === kind || (/^\s+$/.test(text) && last.kind !== 'same'))) last.text += text
    else list.push({ text, kind })
  }
  let i = 0
  let j = 0
  while (i < n && j < m) {
    if (norm(a[i]) === norm(b[j])) {
      push(left, a[i++], 'same')
      push(right, b[j++], 'same')
    } else if (dp[i + 1][j] >= dp[i][j + 1]) push(left, a[i++], 'del')
    else push(right, b[j++], 'add')
  }
  while (i < n) push(left, a[i++], 'del')
  while (j < m) push(right, b[j++], 'add')
  return { before: left, after: right }
}
