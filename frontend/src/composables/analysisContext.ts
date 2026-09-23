import { inject, type ComputedRef, type InjectionKey, type Ref } from 'vue'
import type { Analysis, Finding, FindingType, Severity } from '@/api/types'
import type { SortKey } from '@/utils/findings'

export interface TableFilters {
  query: string
  types: FindingType[]
  risk: Severity | 'all'
  sort: SortKey
}

export interface AnalysisContext {
  analysis: Ref<Analysis | null>
  findings: ComputedRef<Finding[]>
  filters: TableFilters
  /** Findings after search, filters and sort — the order ↑/↓ follows in the panel. */
  visible: ComputedRef<Finding[]>
  resetFilters: () => void
  openFinding: (id: string, from?: 'table' | 'all') => void
  selectedId: ComputedRef<string | null>
  /** Short label shown to people: the backend id if it is already «F-01», else a priority index. */
  labelOf: (id: string) => string
}

export const ANALYSIS_CTX: InjectionKey<AnalysisContext> = Symbol('analysis')

export function useAnalysisContext(): AnalysisContext {
  const ctx = inject(ANALYSIS_CTX)
  if (!ctx) throw new Error('AnalysisContext is not provided')
  return ctx
}
