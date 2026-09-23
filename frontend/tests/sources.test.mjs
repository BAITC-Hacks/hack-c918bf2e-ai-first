// Regression: evidence sides follow the contract (before = ДО, after = ПОСЛЕ) for every
// finding type; missing quotes are described cautiously; demo marking survives copying.
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { loadModule } from './helpers.mjs'

const { evidenceSides, MISSING_TITLE } = await loadModule('src/utils/evidence.ts')
const { locatorLabel, citation } = await loadModule('src/utils/findings.ts')
const { buildConclusion, conclusionPlainText } = await loadModule('src/utils/conclusion.ts')
const { DEMO_NOTICE } = await loadModule('src/utils/demo.ts')

const ev = (document, clause) => ({ document, clause, quote: 'Цитата', department: 'Отдел', page: null })
const finding = (type, before, after) => ({
  id: 'f1', type, severity: 'high', title: 'Вывод', explanation: 'Пояснение', confidence: 0.9, before, after, recommendation: 'Проверить',
})

// 1. Duplicate keeps ДО / ПОСЛЕ and the original objects.
const b = ev('до.docx', '1.1')
const a = ev('после.docx', '2.1')
const [left, right] = evidenceSides(finding('duplicate', b, a))
assert.equal(left.badge, 'ДО')
assert.equal(left.setLabel, 'Комплект до')
assert.equal(left.evidence, b)
assert.equal(right.badge, 'ПОСЛЕ')
assert.equal(right.setLabel, 'Комплект после')
assert.equal(right.evidence, a)

// 2. Missing side: cautious wording, no invented claims.
const sides = evidenceSides(finding('lost', b, null))
assert.equal(sides[1].evidence, null)
assert.equal(sides[1].missingTitle, MISSING_TITLE)
for (const s of sides) {
  assert.doesNotMatch(s.missingTitle + s.missingText, /не было|проверил все|не найден[аоы]? ни в одном/i)
}

// 3. Locators are strings: no «п.» for non-numeric locators, no invented page.
assert.equal(locatorLabel('3.4'), 'п. 3.4')
assert.equal(locatorLabel('абзац 12'), 'абзац 12')
assert.equal(locatorLabel('Лист1!7'), 'Лист1!7')
assert.equal(locatorLabel('таблица 2, строка 3'), 'таблица 2, строка 3')
assert.doesNotMatch(citation(ev('до.docx', 'абзац 12')), /стр\./)

// 4. Demo marking is carried into the copied text (and is absent for real runs).
const base = { status: 'completed', title: 'Анализ', findings: [], summary: null, conclusion: 'Текст' }
const demoText = conclusionPlainText({ ...base, id: 'demo-1' }, buildConclusion({ ...base, id: 'demo-1' }))
assert.ok(demoText.startsWith(`[${DEMO_NOTICE}]`), 'demo notice opens the copied text')
assert.ok(demoText.trimEnd().endsWith(`[${DEMO_NOTICE}]`), 'demo notice closes the copied text')
const realText = conclusionPlainText({ ...base, id: 'uuid-1' }, buildConclusion({ ...base, id: 'uuid-1' }))
assert.ok(!realText.includes(DEMO_NOTICE))
// No structural_risks in this result: the text must say the block is unknown, not «no conflicts».
assert.match(realText, /не передал блок рисков внутри редакции/)
assert.doesNotMatch(realText, /конфликт[а-я]* интересов не (выявлен|обнаружен)/i)

// 5. Demo dataset: `before` evidence comes from the «до» set, `after` from «после».
const fixture = JSON.parse(await readFile('src/api/fixtures/demo-analysis.json', 'utf8'))
const beforeDocs = new Set(fixture.files.before.map(([n]) => n))
const afterDocs = new Set(fixture.files.after.map(([n]) => n))
for (const f of fixture.findings) {
  if (f.before) assert.ok(beforeDocs.has(f.before.document), `${f.id}: before must cite a «до» document`)
  if (f.after) assert.ok(afterDocs.has(f.after.document), `${f.id}: after must cite a «после» document`)
}

console.log('Evidence sources and demo marking: 5 regression scenarios passed.')
