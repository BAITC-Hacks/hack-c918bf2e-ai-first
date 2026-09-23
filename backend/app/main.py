import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated
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
    loop = asyncio.get_running_loop()

    async def update_stage(code: str, progress: int) -> None:
        index = next(index for index, step in enumerate(analysis.steps) if step.code == code)
        for position, step in enumerate(analysis.steps):
            step.status = (
                StepStatus.COMPLETED
                if position < index
                else StepStatus.PROCESSING
                if position == index
                else StepStatus.PENDING
            )
        analysis.current_step = analysis.steps[index].title
        analysis.progress = progress
        await store.put(analysis)

    def on_stage(code: str, progress: int) -> None:
        asyncio.run_coroutine_threadsafe(update_stage(code, progress), loop).result(timeout=5)

    try:
        result = await asyncio.to_thread(analyze_documents, before, after, settings, on_stage)
        analysis.findings = result.findings
        analysis.organization_changes = result.organization_changes
        analysis.summary = result.summary
        analysis.warnings = result.warnings
        analysis.agent_trace = result.agent_trace
        analysis.quality_score = result.quality_score
        analysis.function_registry = result.function_registry
        analysis.conclusion = result.conclusion
        for step in analysis.steps:
            step.status = StepStatus.COMPLETED
        analysis.progress = 100
        analysis.status = AnalysisStatus.COMPLETED
        analysis.current_step = "Готово"
        await store.put(analysis)
    except Exception as exc:  # noqa: BLE001 - defensive background job boundary
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
    before_files: Annotated[list[UploadFile], File()],
    after_files: Annotated[list[UploadFile], File()],
    title: Annotated[str, Form()] = "Анализ реорганизации",
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
