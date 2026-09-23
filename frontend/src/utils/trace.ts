// Presentation of agent_trace. Only `summary` is shown to people: the trace never
// carries prompts, and any extra fields a backend might add are ignored.
import type { AgentTraceEntry } from '@/api/types'

export const AGENT_LABEL: Record<string, string> = {
  orchestrator: 'Оркестратор',
  document_tools: 'Инструменты документов',
  comparison_agent: 'Агент сопоставления',
  critic_agent: 'Критик',
  evidence_verifier: 'Верификатор',
}

type Tone = 'neutral' | 'accent' | 'positive' | 'warning'

export const ACTION_META: Record<string, { label: string; icon: string; tone: Tone }> = {
  plan: { label: 'План анализа', icon: 'route', tone: 'accent' },
  extract: { label: 'Извлечение документов', icon: 'description', tone: 'neutral' },
  compare: { label: 'Первичный анализ', icon: 'compare_arrows', tone: 'neutral' },
  evaluate: { label: 'Оценка критика', icon: 'fact_check', tone: 'accent' },
  revise: { label: 'Исправление по замечаниям', icon: 'edit_note', tone: 'warning' },
  're-evaluate': { label: 'Повторная оценка критика', icon: 'fact_check', tone: 'accent' },
  accept_revision: { label: 'Исправление принято', icon: 'task_alt', tone: 'positive' },
  rollback: { label: 'Откат к лучшей версии', icon: 'undo', tone: 'warning' },
  verify: { label: 'Проверка доказательств', icon: 'verified', tone: 'positive' },
}

export const STATUS_META: Record<string, { label: string; icon: string }> = {
  completed: { label: 'Готово', icon: 'check_circle' },
  processing: { label: 'Выполняется', icon: 'autorenew' },
  running: { label: 'Выполняется', icon: 'autorenew' },
  pending: { label: 'Ожидает', icon: 'radio_button_unchecked' },
  failed: { label: 'Ошибка', icon: 'error' },
  skipped: { label: 'Пропущено', icon: 'remove_circle_outline' },
}

const MAX_SUMMARY = 600

export interface TraceView {
  key: string
  agent: string
  label: string
  icon: string
  tone: Tone
  status: string
  statusLabel: string
  statusIcon: string
  summary: string
}

export function toTraceView(entries: AgentTraceEntry[]): TraceView[] {
  return entries.map((e, i) => {
    const action = ACTION_META[e.action]
    const status = STATUS_META[e.status]
    const summary = (e.summary ?? '').trim()
    return {
      key: `${i}-${e.agent}-${e.action}`,
      agent: AGENT_LABEL[e.agent] ?? e.agent,
      label: action?.label ?? e.action,
      icon: action?.icon ?? 'radio_button_checked',
      tone: action?.tone ?? 'neutral',
      status: e.status,
      statusLabel: status?.label ?? e.status,
      statusIcon: status?.icon ?? 'info',
      summary: summary.length > MAX_SUMMARY ? `${summary.slice(0, MAX_SUMMARY - 1)}…` : summary,
    }
  })
}

export type RevisionOutcome = 'none' | 'accepted' | 'rolled_back' | 'revised' | 'pending'

/**
 * Self-correction outcome derived from the trace. A revision without an orchestrator
 * decision is 'pending' while the run is active and plain 'revised' once it has finished
 * (older backends do not emit accept_revision / rollback).
 */
export function revisionOutcome(entries: AgentTraceEntry[], running = false): RevisionOutcome | null {
  if (!entries.some((e) => e.action === 'evaluate')) return null
  const revised = entries.some((e) => e.action === 'revise')
  if (!revised) return 'none'
  if (entries.some((e) => e.action === 'rollback')) return 'rolled_back'
  if (entries.some((e) => e.action === 'accept_revision')) return 'accepted'
  return running ? 'pending' : 'revised'
}
