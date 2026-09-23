// Regression for structural_risks (docs/FRONTEND_RISKS_HANDOFF.md §8): risks inside one
// edition stay separate from findings, keep each evidence side, and null / [] never
// read as «no risks».
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { loadModule } from './helpers.mjs'

const { riskState, riskSideLabel, riskPlainLines, RISK_KIND_META } = await loadModule('src/utils/risks.ts')
const { buildConclusion, conclusionPlainText } = await loadModule('src/utils/conclusion.ts')
const { DEMO_NOTICE } = await loadModule('src/utils/demo.ts')

const ev = (document, clause, quote, department = 'Отдел закупок') => ({ document, clause, quote, department, page: null })
const after = (e) => ({ side: 'after', evidence: e })
const conflict = {
  id: 'risk-example', kind: 'conflict_interest', severity: 'high', title: 'Самопроверка закупок', confidence: 0.86,
  explanation: 'Один отдел выполняет закупки и независимо оценивает собственные операции.',
  evidence: [
    after(ev('after.docx', '3.1', 'Отдел закупок проводит закупки оборудования.')),
    after(ev('after.docx', '3.2', 'Отдел закупок независимо проверяет собственные закупки оборудования.')),
  ],
  recommendation: 'Проверить необходимость разделения исполнения и независимого контроля.',
}
const duplicate = {
  ...conflict, id: 'risk-dup', kind: 'duplicate', severity: 'medium', title: 'Учёт лицензий в двух подразделениях',
  evidence: [after(ev('after.docx', '4.1', 'Ведёт учёт лицензий.', 'ЦУД')), after(ev('after_2.docx', 'абзац 12', 'Учитывает лицензии ПО.', 'ДЦИ'))],
}
const finding = {
  id: 'f1', type: 'lost', severity: 'high', title: 'Потеря функции', explanation: 'Нет в новой редакции.', confidence: 0.9,
  before: ev('before.docx', '1.1', 'Контролирует сроки.'), after: null, recommendation: 'Закрепить функцию.',
}
const base = { id: 'uuid-1', status: 'completed', title: 'Анализ', conclusion: 'Итог', findings: [finding],
  summary: { before_functions: 5, after_functions: 5, unchanged: 3, lost: 1, added: 0, moved: 0, changed: 0, duplicates: 0, high_risk: 1 } }

// 1. after + after stays after + after: side comes from each evidence item.
assert.deepEqual(conflict.evidence.map(riskSideLabel), ['ПОСЛЕ', 'ПОСЛЕ'])
assert.equal(riskSideLabel({ side: 'before', evidence: conflict.evidence[0].evidence }), 'ДО')
const lines = riskPlainLines(riskState({ structural_risks: [conflict] })).join('\n')
assert.doesNotMatch(lines, /(^|\s)ДО:/m, 'an after+after risk must not show a ДО reference')
assert.equal((lines.match(/ПОСЛЕ: /g) ?? []).length, 2)

// 2. Kinds are distinct: a duplicate is never shown as a conflict of interest and vice versa.
const both = riskState({ structural_risks: [duplicate, conflict] })
assert.equal(both.byKind.duplicate, 1)
assert.equal(both.byKind.conflict_interest, 1)
assert.notEqual(RISK_KIND_META.duplicate.label, RISK_KIND_META.conflict_interest.label)
const bothText = riskPlainLines(both).join('\n')
assert.match(bothText, /\[Дублирование функций\] Учёт лицензий/)
assert.match(bothText, /\[Потенциальный конфликт интересов\] Самопроверка закупок/)

// 3. null / undefined / [] are not «no conflicts».
for (const value of [undefined, null]) {
  const s = riskState({ structural_risks: value })
  assert.equal(s.kind, 'missing')
  assert.match(s.headline, /не передал/)
}
const empty = riskState({ structural_risks: [] })
assert.equal(empty.kind, 'empty')
assert.match(empty.headline, /не доказывает/)
for (const s of [riskState({}), empty]) assert.doesNotMatch(s.headline, /(рисков|конфликт[а-я]*) нет\b|не выявлен/i)
const emptyModel = buildConclusion({ ...base, structural_risks: [] })
assert.ok(emptyModel.limitations.some((l) => /не доказывает/.test(l)), 'coverage-style caveat stays next to []')

// 4. Copied conclusion contains every risk reference, quote and recommendation.
const withRisks = { ...base, structural_risks: [conflict, duplicate] }
const model = buildConclusion(withRisks)
const text = conclusionPlainText(withRisks, model)
assert.match(text, /04\. Потенциальные риски внутри редакции/)
for (const r of [conflict, duplicate]) {
  for (const item of r.evidence) {
    assert.ok(text.includes(item.evidence.document), `copy keeps ${item.evidence.document}`)
    assert.ok(text.includes(item.evidence.quote), 'copy keeps the quote')
  }
  assert.ok(text.includes(r.recommendation))
}
assert.match(text, /ПОСЛЕ: after\.docx, п\. 3\.1: «Отдел закупок проводит закупки оборудования\.»/)
assert.match(text, /after_2\.docx, абзац 12/, 'string locators are kept as-is')

// 5. Findings stay the source of summary and key risks; risks are not added to them.
assert.deepEqual(model.keyRisks.map((f) => f.id), ['f1'])
assert.equal(withRisks.summary.high_risk, 1)
assert.ok(model.recommendations.includes(conflict.recommendation), 'risk recommendations join section 05')

// 6. Demo marking survives when risks are present.
const demo = { ...withRisks, id: 'demo-1' }
const demoText = conclusionPlainText(demo, buildConclusion(demo))
assert.ok(demoText.startsWith(`[${DEMO_NOTICE}]`))
assert.ok(demoText.trimEnd().endsWith(`[${DEMO_NOTICE}]`))

// 7. Demo dataset follows the contract: 2–6 quotes, sides match the document sets,
//    at least two distinct locators of one set; duplicates no longer live in findings.
const fixture = JSON.parse(await readFile('src/api/fixtures/demo-analysis.json', 'utf8'))
const sets = { before: new Set(fixture.files.before.map(([n]) => n)), after: new Set(fixture.files.after.map(([n]) => n)) }
assert.ok(fixture.structural_risks.length > 0)
for (const r of fixture.structural_risks) {
  assert.ok(r.evidence.length >= 2 && r.evidence.length <= 6, `${r.id}: 2–6 quotes`)
  for (const item of r.evidence) assert.ok(sets[item.side].has(item.evidence.document), `${r.id}: side matches document set`)
  const locators = new Set(r.evidence.map((i) => `${i.side}|${i.evidence.document}|${i.evidence.clause}`))
  assert.ok(locators.size >= 2, `${r.id}: at least two distinct locators`)
}
assert.ok(!fixture.findings.some((f) => f.type === 'duplicate'), 'new-format duplicates are structural risks')
assert.equal(fixture.summary.duplicates, 0)

console.log('Structural risks: 7 regression scenarios passed.')
