import assert from 'node:assert/strict'
import { mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { createRequire } from 'node:module'
import { build } from 'vite'

const outDir = await mkdtemp(join(tmpdir(), 'ai-first-conclusion-'))
await build({
  configFile: false,
  logLevel: 'error',
  build: { outDir, emptyOutDir: false,
    lib: { entry: 'src/utils/conclusion.ts', formats: ['cjs'], fileName: () => 'conclusion.cjs' } },
})
const require = createRequire(import.meta.url)
const { buildConclusion } = require(join(outDir, 'conclusion.cjs'))
const base = { findings: [], summary: { before_functions: 10, after_functions: 10, unchanged: 2, lost: 0 } }
const noRegistry = buildConclusion(base)
assert.doesNotMatch(noRegistry.completeness, /Все функции.*закреплены/)
assert.match(noRegistry.completeness, /не подтверждает полноту/)
const coverage = {
  total_fragments: 20, reviewed_fragments: 17, unresolved_fragments: 3,
  before_functions: 10, after_functions: 8, matched_before_functions: 6, needs_review_mappings: 4,
}
const withRegistry = buildConclusion({ ...base, function_registry: { coverage, mappings: [] } })
assert.match(withRegistry.completeness, /17 из 20/)
assert.match(withRegistry.completeness, /4 сопоставлений и 3 фрагментов/)
assert.match(withRegistry.completeness, /не доказывают полноту/)
console.log('Conclusion completeness: 2 regression scenarios passed.')
