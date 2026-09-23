// Regression (P1): registry search and status filters over many rows keep the source
// quotes and never drop rows silently.
import assert from 'node:assert/strict'
import { loadModule } from './helpers.mjs'

const { registryRows, filterRows, statusCounts, filterSources } = await loadModule('src/utils/registry.ts')

const fn = (id, side, action, owner, document, clause, quote) => ({
  id, source_id: id.split('-')[0], side, action, owner, evidence: { document, clause, quote, department: owner, page: null },
})
const functions = [
  fn('B1-F01', 'before', 'Контроль договоров аренды', 'Управление собственности', 'до.pdf', '3.4', 'Контролирует исполнение договоров аренды.'),
  fn('B2-F01', 'before', 'Страхование имущества', 'Управление собственности', 'до.pdf', '3.6', 'Организует страхование имущества.'),
  fn('B3-F01', 'before', 'Закупочные процедуры', 'Управление закупок', 'до.docx', 'абзац 12', 'Организует закупки.'),
  fn('A1-F01', 'after', 'Закупочные процедуры', 'Управление закупок', 'после.docx', 'Лист1!7', 'Организует закупки.'),
]
const mappings = [
  { before_id: 'B1-F01', after_ids: [], status: 'lost', explanation: 'Не найдено в новой редакции.' },
  { before_id: 'B2-F01', after_ids: [], status: 'needs_review', explanation: 'Нет однозначного сопоставления.' },
  { before_id: 'B3-F01', after_ids: ['A1-F01'], status: 'unchanged', explanation: 'Сохранена.' },
]
// 300 extra unchanged rows: filters must scale and keep counts exact.
for (let i = 0; i < 300; i++) mappings.push({ before_id: null, after_ids: [], status: 'added', explanation: `Новая функция ${i}` })
const registry = { functions, mappings, source_reviews: [], coverage: {} }
const rows = registryRows(registry)
assert.equal(rows.length, 303)

// 1. Status filter and counts.
assert.equal(statusCounts(rows).needs_review, 1)
assert.equal(filterRows(rows, { query: '', statuses: ['needs_review'] }).length, 1)
assert.equal(filterRows(rows, { query: '', statuses: ['lost', 'needs_review'] }).length, 2)

// 2. Search by function, department, document and string locator; quotes stay attached.
const byFunction = filterRows(rows, { query: 'страхование', statuses: [] })
assert.equal(byFunction.length, 1)
assert.equal(byFunction[0].before.evidence.quote, 'Организует страхование имущества.')
assert.equal(filterRows(rows, { query: 'управление закупок', statuses: [] }).length, 1)
assert.equal(filterRows(rows, { query: 'Лист1!7', statuses: [] }).length, 1)
assert.equal(filterRows(rows, { query: 'абзац 12', statuses: [] }).length, 1)

// 3. Search and status combine; an impossible combination is empty, not an error.
assert.equal(filterRows(rows, { query: 'аренды', statuses: ['lost'] }).length, 1)
assert.equal(filterRows(rows, { query: 'аренды', statuses: ['unchanged'] }).length, 0)

// 4. Unknown function ids do not crash and do not invent a pair.
const broken = registryRows({ functions, mappings: [{ before_id: 'X-F99', after_ids: ['Y-F99'], status: 'needs_review', explanation: '' }], source_reviews: [], coverage: {} })
assert.equal(broken[0].before, null)
assert.deepEqual(broken[0].after, [])

// 5. Source reviews: status and search filters.
const reviews = [
  { source_id: 'B9', side: 'before', document: 'Оргструктура.xlsx', clause: 'Лист1!12', status: 'needs_review', reason: 'Нет глагола обязанности' },
  { source_id: 'A9', side: 'after', document: 'Приказ.pdf', clause: '1.1', status: 'non_functional', reason: 'Вводная часть' },
]
assert.equal(filterSources(reviews, '', 'needs_review').length, 1)
assert.equal(filterSources(reviews, 'приказ', 'all').length, 1)
assert.equal(filterSources(reviews, 'приказ', 'needs_review').length, 0)

console.log('Function registry filters: 5 regression scenarios passed.')
