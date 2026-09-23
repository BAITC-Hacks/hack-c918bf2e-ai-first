// Builds one TypeScript module of src/ into CommonJS so plain Node tests can import it
// (same approach as conclusion.test.mjs, plus the "@/" alias and Vue for stores).
import { mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { createRequire } from 'node:module'
import { build } from 'vite'

const require = createRequire(import.meta.url)

export async function loadModule(entry) {
  const outDir = await mkdtemp(join(tmpdir(), 'ai-first-test-'))
  await build({
    configFile: false,
    logLevel: 'error',
    resolve: { alias: { '@': resolve('src') } },
    define: { 'process.env.NODE_ENV': '"test"' },
    build: {
      outDir,
      emptyOutDir: false,
      minify: false,
      lib: { entry, formats: ['cjs'], fileName: () => 'module.cjs' },
    },
  })
  return require(join(outDir, 'module.cjs'))
}
