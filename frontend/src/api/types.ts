// Mirrors docs/API_CONTRACT.md. Do not change without agreeing with the backend.

export type AnalysisStatus = 'queued' | 'processing' | 'completed' | 'failed'
export type StepStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type FindingType = 'lost' | 'added' | 'moved' | 'changed' | 'duplicate' | 'unchanged'
export type Severity = 'high' | 'medium' | 'low' | 'info'
export type OrganizationChangeStatus = 'created' | 'preserved' | 'transformed' | 'removed'

export interface AnalysisStep {
  code: string
  title: string
  status: StepStatus
}

export interface Evidence {
  department?: string | null
  clause?: string | null
  quote: string
  document: string
  page?: number | null
}

export interface Finding {
  id: string
  type: FindingType
  severity: Severity
  title: string
  explanation: string
  confidence: number
  before: Evidence | null
  after: Evidence | null
  recommendation: string
}

export interface OrganizationChange {
  id: string
  status: OrganizationChangeStatus
  before_name: string | null
  after_name: string | null
  explanation: string
  before: Evidence | null
  after: Evidence | null
}

export interface AnalysisSummary {
  before_functions: number
  after_functions: number
  unchanged: number
  lost: number
  added: number
  moved: number
  changed: number
  duplicates: number
  high_risk: number
}

/** One step of the multi-agent run. Only the public summary is exposed — no prompts or reasoning. */
export interface AgentTraceEntry {
  agent: string
  action: string
  status: string
  summary: string
}

export interface AnalysisError {
  code: string
  message: string
}

export interface Analysis {
  id: string
  title?: string
  status: AnalysisStatus
  progress: number
  current_step: string
  created_at?: string
  steps: AnalysisStep[]
  summary?: AnalysisSummary | null
  findings?: Finding[]
  organization_changes?: OrganizationChange[]
  conclusion?: string | null
  warnings?: string[]
  agent_trace?: AgentTraceEntry[]
  quality_score?: number | null
  error?: AnalysisError | null
}

export interface AnalysisCreated {
  id: string
  status: AnalysisStatus
  created_at: string
}

export interface CreateAnalysisInput {
  title?: string
  beforeFiles: File[]
  afterFiles: File[]
}
