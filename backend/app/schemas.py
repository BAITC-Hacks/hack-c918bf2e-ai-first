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


class DocumentSide(StrEnum):
    BEFORE = "before"
    AFTER = "after"


class SourceReviewStatus(StrEnum):
    FUNCTIONS = "functions"
    NON_FUNCTIONAL = "non_functional"
    NEEDS_REVIEW = "needs_review"


class MappingStatus(StrEnum):
    UNCHANGED = "unchanged"
    MOVED = "moved"
    CHANGED = "changed"
    LOST = "lost"
    ADDED = "added"
    NEEDS_REVIEW = "needs_review"


class SourceReview(BaseModel):
    source_id: str
    side: DocumentSide
    document: str
    clause: str
    status: SourceReviewStatus
    reason: str = ""


class ExtractedFunction(BaseModel):
    id: str
    source_id: str
    side: DocumentSide
    action: str
    owner: str | None = None
    evidence: Evidence


class FunctionMapping(BaseModel):
    before_id: str | None
    after_ids: list[str]
    status: MappingStatus
    explanation: str


class CoverageMetrics(BaseModel):
    total_fragments: int = 0
    reviewed_fragments: int = 0
    unresolved_fragments: int = 0
    before_functions: int = 0
    after_functions: int = 0
    matched_before_functions: int = 0
    needs_review_mappings: int = 0


class FunctionRegistry(BaseModel):
    functions: list[ExtractedFunction] = Field(default_factory=list)
    source_reviews: list[SourceReview] = Field(default_factory=list)
    mappings: list[FunctionMapping] = Field(default_factory=list)
    coverage: CoverageMetrics = Field(default_factory=CoverageMetrics)


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
    function_registry: FunctionRegistry | None = None
    error: AnalysisError | None = None


class AnalysisCreated(BaseModel):
    id: str
    status: AnalysisStatus
    created_at: datetime
