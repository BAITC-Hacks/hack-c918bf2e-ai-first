// structural_risks: potential risks inside one edition. Kept apart from findings —
// summary counters and the deviations table count findings only.
import type { Analysis, RiskEvidence, Severity, StructuralRisk, StructuralRiskKind } from '../api/types'
import { locatorLabel } from './findings'

export const RISK_KIND_META: Record<StructuralRiskKind, { label: string; icon: string; note: string }> = {
  duplicate: {
    label: 'Дублирование функций',
    icon: 'control_point_duplicate',
    note: 'Одна функция закреплена в нескольких пунктах одной редакции.',
  },
  conflict_interest: {
    label: 'Потенциальный конфликт интересов',
    icon: 'gavel',
    note: 'Гипотеза для проверки специалистом, не юридическое заключение.',
  },
}
export const RISK_KIND_ORDER: StructuralRiskKind[] = ['conflict_interest', 'duplicate']
const SEVERITY_RANK: Record<Severity, number> = { high: 0, medium: 1, low: 2, info: 3 }

export type RiskBlockKind = 'missing' | 'empty' | 'present'

export interface RiskState {
  kind: RiskBlockKind
  risks: StructuralRisk[]
  byKind: Record<StructuralRiskKind, number>
  bySeverity: Record<Severity, number>
  /** One sentence for the overview, conclusion and copied text. */
  headline: string
}

export const RISKS_CAVEAT =
  'Риски внутри редакции — гипотезы модели с проверенными цитатами. Смысловую обоснованность оценил критик; ' +
  'это не юридическое заключение и не измеренная точность.'

export function riskState(a: Pick<Analysis, 'structural_risks'>): RiskState {
  const byKind = { duplicate: 0, conflict_interest: 0 } as Record<StructuralRiskKind, number>
  const bySeverity = { high: 0, medium: 0, low: 0, info: 0 } as Record<Severity, number>
  const list = a.structural_risks
  if (list == null) {
    return {
      kind: 'missing', risks: [], byKind, bySeverity,
      headline: 'Сервис не передал блок рисков внутри редакции (старая версия анализа или блок ещё не готов). Проверка дублирования и конфликтов интересов внутри редакции для этого результата неизвестна.',
    }
  }
  const risks = [...list].sort(
    (x, y) => SEVERITY_RANK[x.severity] - SEVERITY_RANK[y.severity] ||
      RISK_KIND_ORDER.indexOf(x.kind) - RISK_KIND_ORDER.indexOf(y.kind) || y.confidence - x.confidence,
  )
  risks.forEach((r) => {
    byKind[r.kind] += 1
    bySeverity[r.severity] += 1
  })
  if (!risks.length) {
    return {
      kind: 'empty', risks, byKind, bySeverity,
      headline: 'В принятых результатах риски внутри редакции не указаны. Это не доказывает, что дублирования или конфликта интересов нет.',
    }
  }
  return {
    kind: 'present', risks, byKind, bySeverity,
    headline: `Потенциальных рисков внутри редакции: ${risks.length} (дублирование — ${byKind.duplicate}, конфликт интересов — ${byKind.conflict_interest}).`,
  }
}

/** Side comes from each evidence item — never from its position in the list. */
export function riskSideLabel(item: RiskEvidence): 'ДО' | 'ПОСЛЕ' {
  return item.side === 'before' ? 'ДО' : 'ПОСЛЕ'
}

export function riskSourceLine(item: RiskEvidence): string {
  const e = item.evidence
  const where = [e.document, e.clause ? locatorLabel(e.clause) : null, e.page ? `стр. ${e.page}` : null].filter(Boolean).join(', ')
  return `${riskSideLabel(item)}: ${where}`
}

/** Plain-text lines for the copied / printed conclusion. */
export function riskPlainLines(state: RiskState): string[] {
  const lines = [state.headline]
  if (state.kind !== 'present') return lines
  lines.push(RISKS_CAVEAT)
  state.risks.forEach((r, i) => {
    lines.push(`${i + 1}. [${RISK_KIND_META[r.kind].label}] ${r.title}. ${r.explanation}`)
    r.evidence.forEach((item) => lines.push(`   — ${riskSourceLine(item)}: «${item.evidence.quote}»`))
    lines.push(`   Рекомендация (требует подтверждения): ${r.recommendation}`)
  })
  return lines
}
