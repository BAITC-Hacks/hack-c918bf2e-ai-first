// In-memory form state for /new. Survives navigation so "Повторить запуск" can
// resubmit the same files; not persisted across reloads.
import { reactive } from 'vue'

export type FileStatus = 'uploading' | 'ready' | 'error'

export interface FileEntry {
  id: string
  name: string
  size: number
  file: File | null // null for demo placeholders
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
  before: [] as FileEntry[],
  after: [] as FileEntry[],
})

let seq = 0
const nextId = () => `file-${++seq}`

export function validate(name: string, size: number): string | undefined {
  if (!ALLOWED.test(name)) {
    const ext = name.includes('.') ? name.slice(name.lastIndexOf('.')).toLowerCase() : 'без расширения'
    return `Формат ${ext} не поддерживается — загрузите DOCX, PDF или XLSX`
  }
  if (size > MAX_FILE_MB * 1024 * 1024) return `Файл больше ${MAX_FILE_MB} МБ — разделите документ или сожмите PDF`
  return undefined
}

export function addFiles(set: SetKey, files: File[]): number {
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
  return skipped
}

export function removeFile(set: SetKey, id: string) {
  draft[set] = draft[set].filter((f) => f.id !== id)
}

/** Demo: files appear with a 110 ms stagger and a short visible upload. */
export function fillDemo(files: { before: Array<[string, number]>; after: Array<[string, number]> }, title: string) {
  draft.title = title
  draft.before = []
  draft.after = []
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const queue: Array<[SetKey, string, number]> = [
    ...files.before.map(([n, s]) => ['before', n, s] as [SetKey, string, number]),
    ...files.after.map(([n, s]) => ['after', n, s] as [SetKey, string, number]),
  ]
  queue.forEach(([set, name, size], i) => {
    const push = () => {
      const entry: FileEntry = { id: nextId(), name, size, file: null, status: reduce ? 'ready' : 'uploading', progress: reduce ? 1 : 0.15 }
      draft[set].push(entry)
      if (reduce) return
      const update = (patch: Partial<FileEntry>) => {
        const target = draft[set].find((f) => f.id === entry.id)
        if (target) Object.assign(target, patch)
      }
      window.setTimeout(() => update({ progress: 0.6 }), 180)
      window.setTimeout(() => update({ progress: 1, status: 'ready' }), 420)
    }
    if (reduce) push()
    else window.setTimeout(push, i * 110)
  })
}

export function readyFiles(set: SetKey): FileEntry[] {
  return draft[set].filter((f) => f.status === 'ready')
}

export function isDemoDraft(): boolean {
  return [...draft.before, ...draft.after].some((f) => f.file === null)
}

/** Facts about runs started in this tab (the contract does not return file counts). */
export const runMeta = new Map<string, { before: number; after: number }>()
