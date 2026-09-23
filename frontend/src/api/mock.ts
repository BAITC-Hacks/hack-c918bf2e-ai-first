// Demo only: prepared data for showing the interface — no documents are analysed.
// Local stand-in for the backend. Serves handoff/demo-analysis.json converted to the
// docs/API_CONTRACT.md shape and simulates the five pipeline steps.
import fixture from './fixtures/demo-analysis.json'
import type {
  AgentTraceEntry, Analysis, AnalysisCreated, AnalysisStep, Finding, FunctionRegistry, OrganizationChange, StructuralRisk,
} from './types'

const MOCK_PREFIX = 'demo-'
const QUEUE_MS = 600
const STEP_MS = [1800, 2300, 2800, 2000, 1400]

const STEP_DEFS: Array<Pick<AnalysisStep, 'code' | 'title'>> = [
  { code: 'extract', title: 'Извлечение документов' },
  { code: 'structure', title: 'Выделение структуры и функций' },
  { code: 'compare', title: 'Семантическое сопоставление' },
  { code: 'verify', title: 'Проверка доказательств' },
  { code: 'report', title: 'Формирование заключения' },
]

export const DEMO_FILES = fixture.files as { before: Array<[string, number]>; after: Array<[string, number]> }
export const DEMO_TITLE = fixture.title

const TRACE = fixture.agent_trace as AgentTraceEntry[]

/**
 * How many trace entries are visible at a moment of the demo run: the mock reveals
 * them while the pipeline advances so the run screen shows the agents at work.
 */
function traceCount(active: number, fraction: number): number {
  if (active === 0) return fraction > 0.2 ? 1 : 0 // plan
  if (active === 1) return 2 // + extract
  if (active === 2) return 2 + Math.min(5, Math.floor(fraction * 6)) // compare → critic → revise → re-evaluate → accept
  return 7 // verify is added once evidence checking finishes
}

const runs = new Map<string, { title: string; createdAt: number }>()

export function isMockId(id: string): boolean {
  return id.startsWith(MOCK_PREFIX)
}

export function createMockAnalysis(title?: string): AnalysisCreated {
  const id = `${MOCK_PREFIX}${Date.now().toString(36)}`
  const createdAt = Date.now()
  runs.set(id, { title: title?.trim() || DEMO_TITLE, createdAt })
  return { id, status: 'queued', created_at: new Date(createdAt).toISOString() }
}

export function getMockAnalysis(id: string): Analysis {
  let run = runs.get(id)
  if (!run) {
    // Reloaded page or shared link: the demo is already finished.
    run = { title: DEMO_TITLE, createdAt: Date.now() - 120_000 }
    runs.set(id, run)
  }
  const base = { id, title: run.title, created_at: new Date(run.createdAt).toISOString() }
  const elapsed = Date.now() - run.createdAt

  if (elapsed < QUEUE_MS) {
    return { ...base, status: 'queued', progress: 0, current_step: 'В очереди', steps: STEP_DEFS.map((s) => ({ ...s, status: 'pending' })) }
  }

  let t = elapsed - QUEUE_MS
  const total = STEP_MS.reduce((a, b) => a + b, 0)
  if (t < total) {
    let active = 0
    while (t >= STEP_MS[active]) t -= STEP_MS[active++]
    const done = STEP_MS.slice(0, active).reduce((a, b) => a + b, 0) + t
    const trace = TRACE.slice(0, traceCount(active, t / STEP_MS[active]))
    return {
      ...base,
      status: 'processing',
      progress: Math.min(99, Math.round((done / total) * 100)),
      current_step: STEP_DEFS[active].title,
      steps: STEP_DEFS.map((s, i) => ({ ...s, status: i < active ? 'completed' : i === active ? 'processing' : 'pending' })),
      agent_trace: trace,
    }
  }

  return {
    ...base,
    status: 'completed',
    progress: 100,
    current_step: 'Готово',
    steps: STEP_DEFS.map((s) => ({ ...s, status: 'completed' })),
    summary: fixture.summary,
    organization_changes: fixture.organization_changes as OrganizationChange[],
    findings: fixture.findings as Finding[],
    function_registry: fixture.function_registry as FunctionRegistry,
    structural_risks: fixture.structural_risks as StructuralRisk[],
    conclusion: fixture.conclusion,
    warnings: fixture.warnings,
    agent_trace: TRACE,
    quality_score: fixture.quality_score,
  }
}
