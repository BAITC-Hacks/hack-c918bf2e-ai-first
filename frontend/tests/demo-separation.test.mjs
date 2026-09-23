// Regression: a demo form must never be submitted together with real documents, and
// «Повторить запуск» must only resend the files of the run that failed.
import assert from 'node:assert/strict'
import { loadModule } from './helpers.mjs'

const d = await loadModule('src/stores/draft.ts')
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const demoFiles = { before: [['До_1.docx', 100], ['До_2.pdf', 200]], after: [['После_1.docx', 300]] }
const real = (name) => new File(['text'], name)

// 1. Demo form → submission carries no files and is in demo mode.
d.fillDemo(demoFiles, 'Демо-анализ')
await sleep(1000)
assert.equal(d.draft.mode, 'demo')
assert.equal(d.isDemoDraft(), true)
let s = d.submission()
assert.equal(s.mode, 'demo')
assert.equal(s.beforeFiles.length + s.afterFiles.length, 0)

// 2. Adding a real document drops every placeholder and switches to real mode.
const added = d.addFiles('before', [real('Положение_до.docx')])
assert.equal(added.clearedDemo, true)
assert.equal(d.draft.mode, 'real')
assert.equal(d.isDemoDraft(), false)
assert.ok([...d.draft.before, ...d.draft.after].every((f) => f.file !== null), 'no placeholders may remain')
assert.equal(d.draft.title, '', 'demo title is cleared with the demo')
d.addFiles('after', [real('Положение_после.docx')])
s = d.submission()
assert.equal(s.mode, 'real')
assert.deepEqual(s.beforeFiles.map((f) => f.name), ['Положение_до.docx'])
assert.deepEqual(s.afterFiles.map((f) => f.name), ['Положение_после.docx'])

// 3. Pending demo timers cannot re-add placeholders after the switch.
d.fillDemo(demoFiles, 'Демо-анализ')
d.addFiles('before', [real('Свой.docx')])
await sleep(1000)
assert.ok([...d.draft.before, ...d.draft.after].every((f) => f.file !== null), 'late demo timers must not add placeholders')

// 4. Removing every placeholder leaves demo mode.
d.fillDemo(demoFiles, 'Демо')
await sleep(1000)
for (const set of ['before', 'after']) for (const f of [...d.draft[set]]) d.removeFile(set, f.id)
assert.equal(d.draft.mode, 'real')

// 5. Retry uses the failed run's own files, never the current form.
d.resetDraft()
d.addFiles('before', [real('A_до.docx')])
d.addFiles('after', [real('A_после.docx')])
d.rememberRun('run-a', d.submission())
d.resetDraft()
d.addFiles('before', [real('B_до.docx')])
d.addFiles('after', [real('B_после.docx')])
const plan = d.retryPlan('run-a')
assert.equal(plan.kind, 'resend')
assert.deepEqual(plan.before.map((f) => f.name), ['A_до.docx'])
assert.deepEqual(plan.after.map((f) => f.name), ['A_после.docx'])
assert.equal(d.retryPlan('opened-by-link').kind, 'reupload', 'unknown run (reload / link) asks to upload again')
assert.equal(d.retryPlan('demo-123').kind, 'demo')

// 6. A demo run never stores files, so it cannot be resent to the API as real.
d.fillDemo(demoFiles, 'Демо')
d.rememberRun('run-demo-as-real-id', d.submission())
assert.equal(d.retryPlan('run-demo-as-real-id').kind, 'reupload')

console.log('Demo/real separation: 6 regression scenarios passed.')
process.exit(0)
