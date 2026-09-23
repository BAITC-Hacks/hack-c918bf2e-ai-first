// Regression: `completed` is not «everything checked». Incomplete coverage must be
// reported, a missing registry must say coverage is unknown, and neither coverage nor
// the critic score may be presented as accuracy.
import assert from 'node:assert/strict'
import { loadModule } from './helpers.mjs'

const { coverageState, COVERAGE_DISCLAIMER } = await loadModule('src/utils/coverage.ts')
const { buildConclusion, conclusionPlainText } = await loadModule('src/utils/conclusion.ts')

const cov = (over) => ({
  total_fragments: 20, reviewed_fragments: 20, unresolved_fragments: 0, before_functions: 10,
  after_functions: 9, matched_before_functions: 8, needs_review_mappings: 0, ...over,
})
const registry = (c) => ({ functions: [], source_reviews: [], mappings: [], coverage: c })

// 1. Unresolved fragments or open mappings → incomplete, with both numbers in the headline.
const incomplete = coverageState({ function_registry: registry(cov({ unresolved_fragments: 3, needs_review_mappings: 4 })) })
assert.equal(incomplete.kind, 'incomplete')
assert.match(incomplete.headline, /3 фрагм/)
assert.match(incomplete.headline, /4 сопоставл/)

// 2. Fewer reviewed than total is incomplete even without open mappings.
assert.equal(coverageState({ function_registry: registry(cov({ reviewed_fragments: 18 })) }).kind, 'incomplete')

// 3. No registry → unknown, never «complete».
const missing = coverageState({})
assert.equal(missing.kind, 'missing')
assert.match(missing.headline, /неизвест/)
assert.equal(coverageState({ function_registry: null }).kind, 'missing')

// 4. Fully reviewed coverage is «complete» but not described as accuracy.
const complete = coverageState({ function_registry: registry(cov({})) })
assert.equal(complete.kind, 'complete')
assert.doesNotMatch(complete.headline, /точн|верн|правильн/i)
assert.match(COVERAGE_DISCLAIMER, /не точность/)
assert.match(COVERAGE_DISCLAIMER, /не измеренная точность/)

// 5. Conclusion: completed status is explained, coverage limits and critic caveat are in the text.
const analysis = {
  id: 'uuid', status: 'completed', title: 'Анализ', conclusion: 'Итог', findings: [], quality_score: 0.91,
  summary: { before_functions: 10, after_functions: 9, unchanged: 5, lost: 0 },
  function_registry: registry(cov({ unresolved_fragments: 2, needs_review_mappings: 1 })),
}
const model = buildConclusion(analysis)
assert.equal(model.coverage.kind, 'incomplete')
assert.ok(model.limitations.some((l) => /не что все функции проверены/.test(l)))
const text = conclusionPlainText(analysis, model)
assert.match(text, /Ограничения результата/)
assert.match(text, /Охват неполный/)
assert.match(text, /91% \(суждение LLM-контролёра, а не измеренная точность\)/)
assert.match(text, /нет отклонений высокого риска/)
assert.doesNotMatch(text, /Отклонений высокого риска не выявлено/)

// 6. Without a registry the conclusion says coverage is unknown.
const noRegistry = buildConclusion({ ...analysis, function_registry: undefined })
assert.equal(noRegistry.coverage.kind, 'missing')
assert.ok(noRegistry.limitations.some((l) => /охват анализа неизвестен/.test(l)))

console.log('Coverage vs completion: 6 regression scenarios passed.')
