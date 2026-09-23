import type { AnalysisStatus, FindingType, Severity, StepStatus } from '@/api/types'

export const TYPE_META: Record<FindingType, { label: string; color: string; icon: string; hint: string }> = {
  lost: { label: 'Потеря', color: 'loss', icon: 'remove_circle_outline', hint: 'Функция не закреплена после реорганизации' },
  duplicate: { label: 'Дублирование', color: 'dup', icon: 'content_copy', hint: 'Функция закреплена за несколькими подразделениями' },
  changed: { label: 'Изменение', color: 'change', icon: 'edit_note', hint: 'Содержание функции существенно изменено' },
  moved: { label: 'Перемещение', color: 'move', icon: 'swap_horiz', hint: 'Функция передана другому подразделению' },
  added: { label: 'Добавление', color: 'add', icon: 'add_circle_outline', hint: 'Новая функция' },
  unchanged: { label: 'Без изменений', color: 'same', icon: 'check', hint: 'Функция сохранена' },
}

export const TYPE_ORDER: FindingType[] = ['lost', 'duplicate', 'changed', 'moved', 'added', 'unchanged']

export const SEVERITY_META: Record<Severity, { label: string; color: string; rank: number }> = {
  high: { label: 'Высокий', color: 'sev-high', rank: 0 },
  medium: { label: 'Средний', color: 'sev-medium', rank: 1 },
  low: { label: 'Низкий', color: 'sev-low', rank: 2 },
  info: { label: 'Инфо', color: 'sev-info', rank: 3 },
}

export const SEVERITY_ORDER: Severity[] = ['high', 'medium', 'low', 'info']

export const STATUS_META: Record<AnalysisStatus, { label: string; color: string; icon: string }> = {
  queued: { label: 'В очереди', color: 'grey-7', icon: 'schedule' },
  processing: { label: 'Выполняется', color: 'primary', icon: 'autorenew' },
  completed: { label: 'Завершено', color: 'positive', icon: 'check_circle' },
  failed: { label: 'Ошибка', color: 'negative', icon: 'error' },
}

export const STEP_ICON: Record<StepStatus, string> = {
  pending: 'radio_button_unchecked',
  processing: 'autorenew',
  completed: 'check_circle',
  failed: 'cancel',
}

export const STEP_HINT: Record<string, string> = {
  extract: 'Чтение PDF/DOCX, разметка разделов и пунктов',
  structure: 'Подразделения и закреплённые за ними функции',
  compare: 'Семантическое сопоставление функций «до» и «после»',
  verify: 'Контролёр отклоняет выводы без ссылки на пункт документа',
  report: 'Сводка рисков, рекомендации и заключение',
}

export function confidenceLevel(value: number): { label: string; color: string } {
  if (value >= 0.85) return { label: 'Высокая уверенность', color: 'positive' }
  if (value >= 0.6) return { label: 'Средняя уверенность', color: 'warning' }
  return { label: 'Требует проверки экспертом', color: 'negative' }
}

export function percent(value: number): string {
  return `${Math.round(value * 100)} %`
}

export function formatDateTime(iso?: string): string {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('ru-RU', { dateStyle: 'medium', timeStyle: 'short' })
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} КБ`
  return `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} МБ`
}

export function pluralize(n: number, forms: [string, string, string]): string {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return forms[0]
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return forms[1]
  return forms[2]
}
