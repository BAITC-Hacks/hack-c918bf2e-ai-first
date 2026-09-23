// In-memory form state for /new. Not persisted: after a page reload the browser no
// longer has the File objects, so a failed run asks for the documents again.
//
// The form is in exactly one mode. 'demo' holds only placeholders from the prepared
// dataset and never reaches the API; 'real' holds only the user's files. Adding a real
// file to a demo form removes every placeholder first, so the modes cannot mix.
import { reactive } from 'vue'

export type FileStatus = 'uploading' | 'ready' | 'error'
export type DraftMode = 'real' | 'demo'

export interface FileEntry {
  id: string
  name: string
  size: number
  file: File | null // null only for demo placeholders
  status: FileStatus
  progress: number
  error?: string
}

export type SetKey = 'before' | 'after'

export const MAX_FILE_MB = 20
export const MAX_FILES_PER_SET = 30
const ALLOWED = /\.(docx|pdf|xlsx)$/i

export const draft = reactive({
  title: '',
  mode: 'real' as DraftMode,
  before: [] as FileEntry[],
  after: [] as FileEntry[],
})

let seq = 0
const nextId = () => `file-${++seq}`
let demoTimers: ReturnType<typeof setTimeout>[] = []
let demoTitle = ''

export function validate(name: string, size: number): string | undefined {
  if (!ALLOWED.test(name)) {
    const ext = name.includes('.') ? name.slice(name.lastIndexOf('.')).toLowerCase() : 'без расширения'
    return `Формат ${ext} не поддерживается — загрузите DOCX, PDF или XLSX`
  }
  if (size > MAX_FILE_MB * 1024 * 1024) return `Файл больше ${MAX_FILE_MB} МБ — разделите документ или сожмите PDF`
  return undefined
}

function cancelDemoTimers() {
  demoTimers.forEach((t) => clearTimeout(t))
  demoTimers = []
}

/** Drops every demo placeholder and returns the form to real mode. */
export function clearDemo(): boolean {
  if (draft.mode !== 'demo') return false
  cancelDemoTimers()
  draft.before = draft.before.filter((f) => f.file !== null)
  draft.after = draft.after.filter((f) => f.file !== null)
  if (draft.title === demoTitle) draft.title = ''
  draft.mode = 'real'
  return true
}

export function hasRealFiles(): boolean {
  return [...draft.before, ...draft.after].some((f) => f.file !== null)
}

export function addFiles(set: SetKey, files: File[]): { skipped: number; clearedDemo: boolean } {
  const clearedDemo = clearDemo()
  const list = draft[set]
  let skipped = 0
  for (const file of files) {
    if (list.some((f) => f.name === file.name && f.size === file.size)) continue
    if (list.length >= MAX_FILES_PER_SET) {
      skipped += 1
      continue
    }
    const error = validate(file.name, file.size)
    list.push({ id: nextId(), name: file.name, size: file.size, file, status: error ? 'error' : 'ready', progress: 1, error })
  }
  return { skipped, clearedDemo }
}

export function removeFile(set: SetKey, id: string) {
  draft[set] = draft[set].filter((f) => f.id !== id)
  if (draft.mode === 'demo' && !draft.before.length && !draft.after.length) clearDemo()
}

export function resetDraft() {
  cancelDemoTimers()
  draft.title = ''
  draft.mode = 'real'
  draft.before = []
  draft.after = []
}

/**
 * Demo: replaces the whole form with placeholders from the prepared dataset. Callers
 * must confirm first when real files are present (see hasRealFiles).
 */
export function fillDemo(files: { before: Array<[string, number]>; after: Array<[string, number]> }, title: string) {
  resetDraft()
  draft.mode = 'demo'
  draft.title = title
  demoTitle = title
  const reduce = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const queue: Array<[SetKey, string, number]> = [
    ...files.before.map(([n, s]) => ['before', n, s] as [SetKey, string, number]),
    ...files.after.map(([n, s]) => ['after', n, s] as [SetKey, string, number]),
  ]
  const later = (fn: () => void, ms: number) => demoTimers.push(setTimeout(fn, ms))
  queue.forEach(([set, name, size], i) => {
    const push = () => {
      if (draft.mode !== 'demo') return
      const entry: FileEntry = { id: nextId(), name, size, file: null, status: reduce ? 'ready' : 'uploading', progress: reduce ? 1 : 0.15 }
      draft[set].push(entry)
      if (reduce) return
      const update = (patch: Partial<FileEntry>) => {
        const target = draft[set].find((f) => f.id === entry.id)
        if (target) Object.assign(target, patch)
      }
      later(() => update({ progress: 0.6 }), 180)
      later(() => update({ progress: 1, status: 'ready' }), 420)
    }
    if (reduce) push()
    else later(push, i * 110)
  })
}

export function readyFiles(set: SetKey): FileEntry[] {
  return draft[set].filter((f) => f.status === 'ready')
}

export function isDemoDraft(): boolean {
  return draft.mode === 'demo'
}

export interface Submission {
  mode: DraftMode
  title: string
  beforeFiles: File[]
  afterFiles: File[]
  beforeCount: number
  afterCount: number
}

/** What the form would submit right now. Real mode never contains placeholders. */
export function submission(): Submission {
  const before = readyFiles('before')
  const after = readyFiles('after')
  const real = (list: FileEntry[]) => list.flatMap((f) => (f.file ? [f.file] : []))
  return {
    mode: draft.mode,
    title: draft.title,
    beforeFiles: draft.mode === 'real' ? real(before) : [],
    afterFiles: draft.mode === 'real' ? real(after) : [],
    beforeCount: before.length,
    afterCount: after.length,
  }
}

/**
 * Facts about runs started in this tab, keyed by analysis id. `files` are the exact
 * documents sent for that run, so a retry can never pick up another run's files.
 * Lost on reload: the contract has no way to fetch the original documents back.
 */
export interface RunSource {
  mode: DraftMode
  title: string
  before: number
  after: number
  files: { before: File[]; after: File[] } | null
}

export const runSources = new Map<string, RunSource>()

export function rememberRun(id: string, s: Submission) {
  runSources.set(id, {
    mode: s.mode,
    title: s.title,
    before: s.beforeCount,
    after: s.afterCount,
    files: s.mode === 'real' ? { before: s.beforeFiles, after: s.afterFiles } : null,
  })
}

export type RetryPlan =
  | { kind: 'demo'; title: string }
  | { kind: 'resend'; title: string; before: File[]; after: File[] }
  | { kind: 'reupload' }

/**
 * How «Повторить запуск» may restart analysis `id`: only with that run's own files.
 * The current form is never used — it may hold another set of documents.
 */
export function retryPlan(id: string): RetryPlan {
  if (id.startsWith('demo-')) return { kind: 'demo', title: runSources.get(id)?.title ?? '' }
  const source = runSources.get(id)
  if (source?.mode === 'real' && source.files?.before.length && source.files.after.length) {
    return { kind: 'resend', title: source.title, before: source.files.before, after: source.files.after }
  }
  return { kind: 'reupload' }
}
