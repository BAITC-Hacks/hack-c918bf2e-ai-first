// Mirrors docs/API_CONTRACT.md. Do not change without agreeing with the backend.

export type AnalysisStatus = 'queued' | 'processing' | 'completed' | 'failed'
export type StepStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type FindingType = 'lost' | 'added' | 'moved' | 'changed' | 'duplicate' | 'unchanged'
export type Severity = 'high' | 'medium' | 'low' | 'info'

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
  conclusion?: string | null
  warnings?: string[]
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
