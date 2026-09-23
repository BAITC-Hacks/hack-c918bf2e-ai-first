// Single source for the demo disclaimer: shown on every screen of a demo run and
// carried into the copied / printed conclusion.
export const DEMO_NOTICE = 'Демонстрация интерфейса — заранее подготовленные данные, анализ документов не выполняется.'
export const DEMO_SHORT = 'Демонстрация интерфейса'

export function isDemoId(id: string | null | undefined): boolean {
  return typeof id === 'string' && id.startsWith('demo-')
}
