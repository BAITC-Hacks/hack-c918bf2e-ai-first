from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AnalysisStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingType(StrEnum):
    LOST = "lost"
    ADDED = "added"
    MOVED = "moved"
    CHANGED = "changed"
    DUPLICATE = "duplicate"
    UNCHANGED = "unchanged"


class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class OrganizationChangeStatus(StrEnum):
    CREATED = "created"
    PRESERVED = "preserved"
    TRANSFORMED = "transformed"
    REMOVED = "removed"


class AnalysisStep(BaseModel):
    code: str
    title: str
    status: StepStatus = StepStatus.PENDING


class Evidence(BaseModel):
    department: str | None = None
    clause: str | None = None
    quote: str
    document: str
    page: int | None = None


class Finding(BaseModel):
    id: str
    type: FindingType
    severity: Severity
    title: str
    explanation: str
    confidence: float = Field(ge=0, le=1)
    before: Evidence | None = None
    after: Evidence | None = None
    recommendation: str


class OrganizationChange(BaseModel):
    id: str
    status: OrganizationChangeStatus
    before_name: str | None = None
    after_name: str | None = None
    explanation: str
    before: Evidence | None = None
    after: Evidence | None = None


class AnalysisSummary(BaseModel):
    before_functions: int = 0
    after_functions: int = 0
    unchanged: int = 0
    lost: int = 0
    added: int = 0
    moved: int = 0
    changed: int = 0
    duplicates: int = 0
    high_risk: int = 0


class AnalysisError(BaseModel):
    code: str
    message: str


class AgentTraceEntry(BaseModel):
    agent: str
    action: str
    status: str
    summary: str


class Analysis(BaseModel):
    id: str
    title: str
    status: AnalysisStatus
    progress: int = Field(ge=0, le=100)
    current_step: str
    created_at: datetime
    steps: list[AnalysisStep]
    summary: AnalysisSummary | None = None
    findings: list[Finding] = []
    organization_changes: list[OrganizationChange] = []
    conclusion: str | None = None
    warnings: list[str] = []
    agent_trace: list[AgentTraceEntry] = []
    quality_score: float | None = Field(default=None, ge=0, le=1)
    error: AnalysisError | None = None


class AnalysisCreated(BaseModel):
    id: str
    status: AnalysisStatus
    created_at: datetime
