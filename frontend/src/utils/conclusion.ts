// The contract returns `conclusion` as free text. Sections 02–05 of the conclusion
// document are derived from accepted findings and coverage, not a guarantee of completeness.
import type { Analysis, Evidence, Finding } from '@/api/types'
import { sortFindings } from './findings'
import { FUNCS_WORD, TYPE_META, pluralize } from './labels'

export interface ConclusionModel {
  summary: string[]
  keyRisks: Finding[]
  completeness: string
  conflicts: Finding[]
  recommendations: string[]
}

export function buildConclusion(a: Analysis, labelOf: (id: string) => string = (id) => id): ConclusionModel {
  const findings = sortFindings(a.findings ?? [], 'priority')
  const s = a.summary
  const lost = findings.filter((f) => f.type === 'lost')

  let completeness = 'Сводные показатели не получены.'
  if (a.function_registry) {
    const coverage = a.function_registry.coverage
    const potentialLosses = a.function_registry.mappings.filter(row => row.status === 'lost').length
    completeness = `Рассмотрено ${coverage.reviewed_fragments} из ${coverage.total_fragments} текстовых фрагментов. `
      + `В реестре ${coverage.before_functions} записей функций ДО и ${coverage.after_functions} ПОСЛЕ; `
      + `сопоставлено с новой редакцией ${coverage.matched_before_functions} функций ДО. `
      + `Потенциальных потерь в реестре: ${potentialLosses}. `
      + `Требуют проверки: ${coverage.needs_review_mappings} сопоставлений и ${coverage.unresolved_fragments} фрагментов. `
      + 'Эти показатели не доказывают полноту извлечения и распределения функций; требуется экспертная проверка.'
  } else if (s) {
    const base = `Из ${s.before_functions} ${pluralize(s.before_functions, FUNCS_WORD)} комплекта «до» ${s.unchanged} сохранены без изменений.`
    if (s.lost > 0) {
      const names = lost.map((f) => `«${f.title}» (${labelOf(f.id)})`).join(', ')
      completeness = `${base} Выявлено потенциальных потерь: ${s.lost}${names ? `: ${names}` : ''}. Полнота распределения функций не подтверждена.`
    } else {
      completeness = `${base} Потенциальные потери в принятых находках не указаны. Это не подтверждает полноту распределения функций.`
    }
  }

  const recommendations: string[] = []
  for (const f of findings) {
    if (f.severity !== 'high' && f.severity !== 'medium') continue
    const text = f.recommendation.trim()
    if (text && !recommendations.includes(text)) recommendations.push(text)
  }

  return {
    summary: (a.conclusion ?? '').split(/\n{2,}/).map((p) => p.trim()).filter(Boolean),
    keyRisks: findings.filter((f) => f.severity === 'high'),
    completeness,
    conflicts: findings.filter((f) => f.type === 'duplicate'),
    recommendations,
  }
}

export function sourceLine(e: Evidence | null | undefined): string {
  if (!e) return ''
  return [e.document, e.clause ? `п. ${e.clause}` : null, e.page ? `стр. ${e.page}` : null].filter(Boolean).join(', ')
}

export function conclusionPlainText(
  a: Analysis,
  model: ConclusionModel,
  labelOf: (id: string) => string = (id) => id,
): string {
  const lines: string[] = [`АНАЛИТИЧЕСКОЕ ЗАКЛЮЧЕНИЕ`, a.title || 'Анализ без названия', '']
  lines.push('01. Резюме', ...model.summary, '')
  lines.push('02. Ключевые риски')
  if (model.keyRisks.length) {
    model.keyRisks.forEach((f) =>
      lines.push(`— ${labelOf(f.id)} · ${TYPE_META[f.type].label}: ${f.title}. Источник: ${sourceLine(f.before ?? f.after)}`),
    )
  } else lines.push('Отклонений высокого риска не выявлено.')
  lines.push('', '03. Полнота распределения функций', model.completeness, '')
  lines.push('04. Потенциальные конфликты интересов')
  if (model.conflicts.length) model.conflicts.forEach((f, i) => lines.push(`${i + 1}. ${f.explanation} (${labelOf(f.id)})`))
  else lines.push('Не выявлено.')
  lines.push('', '05. Рекомендации (каждая требует подтверждения ответственным сотрудником)')
  model.recommendations.forEach((r, i) => lines.push(`${i + 1}. ${r}`))
  if (a.quality_score != null || a.warnings?.length) {
    lines.push('', 'Контроль качества')
    if (a.quality_score != null) lines.push(`— Оценка критика: ${Math.round(a.quality_score * 100)}%`)
    lines.push(...(a.warnings ?? []).map((w) => `— ${w}`))
  }
  lines.push(
    '',
    'Заключение сформировано ИИ-агентом «Сверка» и носит рекомендательный характер. Выводы подлежат проверке ответственным сотрудником до принятия решения.',
  )
  return lines.join('\n')
}
