// Evidence sides for a finding. `before` always belongs to the «до» set and `after`
// to the «после» set — also for duplicates. Nothing is inferred when a side is absent.
import type { Evidence, Finding } from '../api/types'

export interface EvidenceSide {
  side: 'before' | 'after'
  badge: 'ДО' | 'ПОСЛЕ'
  setLabel: 'Комплект до' | 'Комплект после'
  evidence: Evidence | null
  missingTitle: string
  missingText: string
}

export const MISSING_TITLE = 'Подтверждённый фрагмент не представлен'

export function evidenceSides(f: Finding): [EvidenceSide, EvidenceSide] {
  return [
    {
      side: 'before',
      badge: 'ДО',
      setLabel: 'Комплект до',
      evidence: f.before ?? null,
      missingTitle: MISSING_TITLE,
      missingText: 'Сервис не передал цитату из комплекта «до» для этого вывода.',
    },
    {
      side: 'after',
      badge: 'ПОСЛЕ',
      setLabel: 'Комплект после',
      evidence: f.after ?? null,
      missingTitle: MISSING_TITLE,
      missingText: 'Сервис не передал цитату из комплекта «после» для этого вывода.',
    },
  ]
}
