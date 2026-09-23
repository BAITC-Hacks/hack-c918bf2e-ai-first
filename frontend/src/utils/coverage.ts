// Processing coverage from function_registry.coverage. `status: completed` only means
// the pipeline finished; coverage says how much was reviewed; neither is accuracy.
import type { Analysis } from '../api/types'

export type CoverageKind = 'missing' | 'incomplete' | 'complete'

export interface CoverageState {
  kind: CoverageKind
  totalFragments: number
  reviewedFragments: number
  unresolvedFragments: number
  needsReviewMappings: number
  beforeFunctions: number
  matchedBeforeFunctions: number
  /** One sentence for banners, the drawer and the conclusion. */
  headline: string
}

export const COVERAGE_DISCLAIMER =
  'Охват показывает, какая часть фрагментов и сопоставлений обработана, — это не точность. ' +
  'Оценка критика — суждение LLM-контролёра, а не измеренная точность.'

export function coverageState(a: Pick<Analysis, 'function_registry'>): CoverageState {
  const c = a.function_registry?.coverage
  if (!c) {
    return {
      kind: 'missing', totalFragments: 0, reviewedFragments: 0, unresolvedFragments: 0,
      needsReviewMappings: 0, beforeFunctions: 0, matchedBeforeFunctions: 0,
      headline: 'Сервис не передал реестр функций — охват анализа неизвестен.',
    }
  }
  const incomplete = c.unresolved_fragments > 0 || c.needs_review_mappings > 0 || c.reviewed_fragments < c.total_fragments
  const parts: string[] = []
  if (c.unresolved_fragments > 0) parts.push(`${c.unresolved_fragments} фрагм. без решения`)
  if (c.needs_review_mappings > 0) parts.push(`${c.needs_review_mappings} сопоставл. требуют проверки`)
  if (c.reviewed_fragments < c.total_fragments) parts.push(`рассмотрено фрагментов: ${c.reviewed_fragments} из ${c.total_fragments}`)
  return {
    kind: incomplete ? 'incomplete' : 'complete',
    totalFragments: c.total_fragments,
    reviewedFragments: c.reviewed_fragments,
    unresolvedFragments: c.unresolved_fragments,
    needsReviewMappings: c.needs_review_mappings,
    beforeFunctions: c.before_functions,
    matchedBeforeFunctions: c.matched_before_functions,
    headline: incomplete
      ? `Охват неполный: ${parts.join(', ')}.`
      : `Все ${c.total_fragments} фрагментов рассмотрены, открытых сопоставлений нет.`,
  }
}
