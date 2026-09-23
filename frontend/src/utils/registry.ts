// Rows and filters for the function registry table. Pure so it can be tested: real
// analyses return hundreds of mappings and source reviews.
import type { ExtractedFunction, FunctionMapping, FunctionRegistry, MappingStatus, SourceReview } from '../api/types'

export const MAPPING_LABEL: Record<MappingStatus, string> = {
  needs_review: 'Требует проверки',
  lost: 'Потенциальная потеря',
  added: 'Новая',
  changed: 'Изменена',
  moved: 'Передана',
  unchanged: 'Сохранена',
}
export const MAPPING_ORDER: MappingStatus[] = ['needs_review', 'lost', 'added', 'changed', 'moved', 'unchanged']

export const SOURCE_LABEL: Record<SourceReview['status'], string> = {
  needs_review: 'Требует проверки',
  functions: 'Функции извлечены',
  non_functional: 'Нефункциональный',
}

export interface RegistryRow extends FunctionMapping {
  key: string
  before: ExtractedFunction | null
  after: ExtractedFunction[]
  /** Lower-cased text for search: functions, owners, departments, documents, locators, explanation. */
  haystack: string
}

const fnText = (f: ExtractedFunction | null | undefined) =>
  f ? [f.action, f.owner, f.evidence.department, f.evidence.document, f.evidence.clause, f.evidence.quote].filter(Boolean).join(' ') : ''

export function registryRows(registry: FunctionRegistry): RegistryRow[] {
  const byId = new Map(registry.functions.map((f) => [f.id, f]))
  return registry.mappings.map((m, index) => {
    const before = m.before_id ? byId.get(m.before_id) ?? null : null
    const after = m.after_ids.map((id) => byId.get(id)).filter((f): f is ExtractedFunction => !!f)
    return {
      ...m,
      key: `${index}-${m.before_id ?? 'new'}`,
      before,
      after,
      haystack: [fnText(before), ...after.map(fnText), m.explanation].join(' ').toLowerCase(),
    }
  })
}

export interface RegistryFilter {
  query: string
  statuses: MappingStatus[]
}

export function filterRows(rows: RegistryRow[], f: RegistryFilter): RegistryRow[] {
  const terms = f.query.trim().toLowerCase().split(/\s+/).filter(Boolean)
  return rows.filter(
    (r) => (!f.statuses.length || f.statuses.includes(r.status)) && terms.every((t) => r.haystack.includes(t)),
  )
}

export function statusCounts(rows: RegistryRow[]): Record<MappingStatus, number> {
  const counts = Object.fromEntries(MAPPING_ORDER.map((s) => [s, 0])) as Record<MappingStatus, number>
  rows.forEach((r) => (counts[r.status] += 1))
  return counts
}

export function filterSources(list: SourceReview[], query: string, status: SourceReview['status'] | 'all'): SourceReview[] {
  const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean)
  return list.filter((s) => {
    if (status !== 'all' && s.status !== status) return false
    const text = [s.document, s.clause, s.reason, s.side === 'before' ? 'до' : 'после'].join(' ').toLowerCase()
    return terms.every((t) => text.includes(t))
  })
}
