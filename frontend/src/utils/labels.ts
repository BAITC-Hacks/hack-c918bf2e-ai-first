import type { FindingType, OrganizationChangeStatus, Severity, StepStatus } from '@/api/types'

// Colours reference --sv-* tokens (src/css/tokens.scss) so both themes work.
export const TYPE_META: Record<FindingType, { label: string; icon: string; fg: string; bg: string }> = {
  lost: { label: 'Потеряна', icon: 'remove_circle_outline', fg: 'var(--sv-high)', bg: 'var(--sv-high-bg)' },
  duplicate: { label: 'Дублирование', icon: 'control_point_duplicate', fg: 'var(--sv-duplicate)', bg: 'var(--sv-duplicate-bg)' },
  changed: { label: 'Изменена', icon: 'change_circle', fg: 'var(--sv-medium)', bg: 'var(--sv-medium-bg)' },
  moved: { label: 'Перемещена', icon: 'east', fg: 'var(--sv-moved)', bg: 'var(--sv-moved-bg)' },
  added: { label: 'Новая', icon: 'add_circle_outline', fg: 'var(--sv-low)', bg: 'var(--sv-low-bg)' },
  unchanged: { label: 'Без изменений', icon: 'check_circle_outline', fg: 'var(--sv-muted)', bg: 'var(--sv-line)' },
}

/** Priority order from the brief: lost → duplicate → changed → moved → added. */
export const TYPE_ORDER: FindingType[] = ['lost', 'duplicate', 'changed', 'moved', 'added', 'unchanged']

export const SEVERITY_META: Record<Severity, { label: string; icon: string; rank: number }> = {
  high: { label: 'Высокий', icon: 'error', rank: 0 },
  medium: { label: 'Средний', icon: 'warning_amber', rank: 1 },
  low: { label: 'Низкий', icon: 'info', rank: 2 },
  info: { label: 'Инфо', icon: 'info', rank: 3 },
}

export const ORG_META: Record<OrganizationChangeStatus, { label: string; icon: string; fg: string; order: number }> = {
  removed: { label: 'Упразднено', icon: 'indeterminate_check_box', fg: 'var(--sv-high)', order: 0 },
  created: { label: 'Создано', icon: 'add_box', fg: 'var(--sv-low)', order: 1 },
  transformed: { label: 'Преобразовано', icon: 'sync_alt', fg: 'var(--sv-moved)', order: 2 },
  preserved: { label: 'Сохранено', icon: 'check', fg: 'var(--sv-muted)', order: 3 },
}

export const STEP_META: Record<StepStatus, { label: string; icon: string; fg: string }> = {
  pending: { label: 'Ожидает', icon: 'radio_button_unchecked', fg: 'var(--sv-dashed)' },
  processing: { label: 'Выполняется', icon: 'autorenew', fg: 'var(--sv-accent)' },
  completed: { label: 'Готово', icon: 'check_circle', fg: 'var(--sv-low)' },
  failed: { label: 'Ошибка', icon: 'error', fg: 'var(--sv-high)' },
}

/** One-line explanations for the five pipeline stages, by position. */
export const STEP_NOTES = [
  'Читаем текст из DOCX, PDF и XLSX, сохраняем номера пунктов и, где они есть, страниц.',
  'Находим подразделения и перечень функций каждого из них.',
  'Сравниваем функции «до» и «после» по смыслу, а не по совпадению слов.',
  'Для каждого вывода ищем точную цитату. Выводы без цитаты исключаются.',
  'Оцениваем риски и готовим заключение с рекомендациями.',
]

export function confidenceLevel(value: number): string {
  if (value >= 0.85) return 'высокая'
  if (value >= 0.7) return 'средняя'
  return 'низкая'
}

export function percent(value: number): string {
  return `${Math.round(value * 100)}%`
}

export function pluralize(n: number, forms: [string, string, string]): string {
  const a = n % 10
  const b = n % 100
  if (a === 1 && b !== 11) return forms[0]
  if (a >= 2 && a <= 4 && (b < 10 || b >= 20)) return forms[1]
  return forms[2]
}

export const FILES: [string, string, string] = ['файл', 'файла', 'файлов']
export const FINDINGS_WORD: [string, string, string] = ['вывод', 'вывода', 'выводов']
export const DOCS_WORD: [string, string, string] = ['документ', 'документа', 'документов']
export const FUNCS_WORD: [string, string, string] = ['функция', 'функции', 'функций']

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} КБ`
  return `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} МБ`
}

export function fileExt(name: string): string {
  const m = /\.([a-z0-9]+)$/i.exec(name)
  return m ? m[1].toUpperCase() : ''
}

export function docIcon(name: string): string {
  const ext = fileExt(name)
  if (ext === 'DOCX' || ext === 'DOC') return 'description'
  if (ext === 'PDF') return 'picture_as_pdf'
  if (ext === 'XLSX' || ext === 'XLS') return 'table_chart'
  return 'insert_drive_file'
}

export function formatDuration(ms: number): string {
  const total = Math.max(0, Math.round(ms / 1000))
  const m = Math.floor(total / 60)
  const s = total % 60
  return m ? `${m} мин ${s} с` : `${s} с`
}

export function formatClock(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000))
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}
