// Regression: the agent journal shows Russian labels only; technical codes never leak
// into visible text, and summaries from the server are kept verbatim.
import assert from 'node:assert/strict'
import { loadModule } from './helpers.mjs'

const { toTraceView, UNKNOWN_ACTION_LABEL, UNKNOWN_AGENT_LABEL } = await loadModule('src/utils/trace.ts')

const entry = (agent, action, status = 'completed', summary = 'Итог шага.') => ({ agent, action, status, summary })
const real = [
  entry('function_extractor', 'inventory'),
  entry('function_matcher', 'match_inventory'),
  entry('evidence_verifier', 'precheck'),
  entry('orchestrator', 'plan'),
  entry('document_tools', 'extract'),
  entry('comparison_agent', 'compare'),
  entry('critic_agent', 'evaluate'),
  entry('comparison_agent', 'revise'),
  entry('critic_agent', 're-evaluate'),
  entry('orchestrator', 'accept_revision'),
  entry('orchestrator', 'rollback'),
  entry('evidence_verifier', 'verify'),
]
const latinCode = /[a-z]+_[a-z]+|\b(inventory|precheck|plan|extract|compare|evaluate|revise|verify|rollback|completed)\b/

// 1. Every stage the backend emits today has a Russian label and agent name.
for (const v of toTraceView(real)) {
  for (const text of [v.label, v.agent, v.statusLabel]) assert.doesNotMatch(text, latinCode, `visible text leaks a code: ${text}`)
}
const [inv, match, pre] = toTraceView(real)
assert.equal(inv.label, 'Реестр функций')
assert.equal(match.label, 'Пакетное сопоставление функций')
assert.equal(pre.label, 'Предварительная проверка источников')

// 2. Unknown stages fall back to neutral Russian text; the code is kept only for a tooltip.
const [unknown] = toTraceView([entry('future_agent', 'new_stage', 'weird_status')])
assert.equal(unknown.label, UNKNOWN_ACTION_LABEL)
assert.equal(unknown.agent, UNKNOWN_AGENT_LABEL)
assert.doesNotMatch(unknown.statusLabel, latinCode)
assert.equal(unknown.code, 'future_agent / new_stage')

// 3. Server summaries are not rewritten.
const summary = 'Извлечено функций ДО/ПОСЛЕ: 532/546. Рассмотрено фрагментов: 971/981.'
assert.equal(toTraceView([entry('function_extractor', 'inventory', 'completed', summary)])[0].summary, summary)

console.log('Agent journal labels: 3 regression scenarios passed.')
