import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.pipeline import analyze_documents
from app.schemas import (
    Analysis,
    AnalysisCreated,
    AnalysisError,
    AnalysisStatus,
    AnalysisStep,
    StepStatus,
)
from app.store import store

settings = get_settings()
app = FastAPI(title="AI First API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STEP_DEFINITIONS = [
    ("extract", "Извлечение документов"),
    ("structure", "Выделение функций"),
    ("compare", "Сопоставление"),
    ("verify", "Проверка доказательств"),
    ("report", "Формирование заключения"),
]
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def save_uploads(analysis_id: str, group: str, files: list[UploadFile]) -> list[Path]:
    target_dir = Path(settings.upload_dir) / analysis_id / group
    target_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    limit = settings.max_file_size_mb * 1024 * 1024

    for upload in files:
        filename = Path(upload.filename or "document").name
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(415, f"Формат {suffix or 'без расширения'} не поддерживается")
        content = await upload.read(limit + 1)
        if len(content) > limit:
            raise HTTPException(413, f"Файл {filename} превышает {settings.max_file_size_mb} МБ")
        path = target_dir / f"{uuid4().hex}_{filename}"
        path.write_bytes(content)
        saved.append(path)
    return saved


async def run_analysis(analysis_id: str, before: list[Path], after: list[Path]) -> None:
    analysis = await store.get(analysis_id)
    if analysis is None:
        return
    analysis.status = AnalysisStatus.PROCESSING
    await store.put(analysis)
    try:
        for index, step in enumerate(analysis.steps[:2]):
            step.status = StepStatus.PROCESSING
            analysis.current_step = step.title
            analysis.progress = index * 20 + 5
            await store.put(analysis)
            await asyncio.sleep(0)
            step.status = StepStatus.COMPLETED
            analysis.progress = (index + 1) * 20

        analysis.steps[2].status = StepStatus.PROCESSING
        analysis.current_step = analysis.steps[2].title
        analysis.progress = 45
        result = await asyncio.to_thread(analyze_documents, before, after, settings)
        analysis.steps[2].status = StepStatus.COMPLETED
        analysis.progress = 70

        analysis.steps[3].status = StepStatus.PROCESSING
        analysis.current_step = analysis.steps[3].title
        analysis.findings = result.findings
        analysis.organization_changes = result.organization_changes
        analysis.summary = result.summary
        analysis.warnings = result.warnings
        analysis.agent_trace = result.agent_trace
        analysis.quality_score = result.quality_score
        analysis.steps[3].status = StepStatus.COMPLETED
        analysis.progress = 90

        analysis.steps[4].status = StepStatus.PROCESSING
        analysis.current_step = analysis.steps[4].title
        analysis.conclusion = result.conclusion
        analysis.steps[4].status = StepStatus.COMPLETED
        analysis.progress = 100
        analysis.status = AnalysisStatus.COMPLETED
        analysis.current_step = "Готово"
        await store.put(analysis)
    except Exception as exc:  # pragma: no cover - defensive job boundary
        analysis.status = AnalysisStatus.FAILED
        analysis.current_step = "Ошибка"
        processing_step = next(
            (step for step in analysis.steps if step.status == StepStatus.PROCESSING), None
        )
        if processing_step:
            processing_step.status = StepStatus.FAILED
        analysis.error = AnalysisError(code="ANALYSIS_ERROR", message=str(exc))
        await store.put(analysis)


@app.post("/api/v1/analyses", response_model=AnalysisCreated, status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(
    before_files: list[UploadFile] = File(...),
    after_files: list[UploadFile] = File(...),
    title: str = Form("Анализ реорганизации"),
) -> AnalysisCreated:
    if not before_files or not after_files:
        raise HTTPException(422, "Нужен хотя бы один документ в каждом комплекте")

    analysis_id = str(uuid4())
    before = await save_uploads(analysis_id, "before", before_files)
    after = await save_uploads(analysis_id, "after", after_files)
    analysis = Analysis(
        id=analysis_id,
        title=title,
        status=AnalysisStatus.QUEUED,
        progress=0,
        current_step="В очереди",
        created_at=datetime.now(UTC),
        steps=[AnalysisStep(code=code, title=step_title) for code, step_title in STEP_DEFINITIONS],
    )
    await store.put(analysis)
    asyncio.create_task(run_analysis(analysis_id, before, after))
    return AnalysisCreated(id=analysis.id, status=analysis.status, created_at=analysis.created_at)


@app.get("/api/v1/analyses/{analysis_id}", response_model=Analysis)
async def get_analysis(analysis_id: str) -> Analysis:
    analysis = await store.get(analysis_id)
    if analysis is None:
        raise HTTPException(404, "Анализ не найден")
    return analysis
