import os
from datetime import UTC, datetime
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from app.schemas import (
    Analysis,
    AnalysisStatus,
    AnalysisStep,
    AnalysisSummary,
    CoverageMetrics,
    Evidence,
    ExtractedFunction,
    Finding,
    FunctionMapping,
    FunctionRegistry,
    SourceReview,
    StepStatus,
)
from app.store import MemoryAnalysisStore, PostgresAnalysisStore


def snapshot(status: str = "completed") -> Analysis:
    evidence = Evidence(document="регламент.docx", clause="1.2", quote="Готовит отчёт.")
    return Analysis(
        id=str(uuid4()), title="Синтетическая проверка сохранения", status=status,
        progress=100 if status == "completed" else 35, current_step="Проверка",
        created_at=datetime.now(UTC),
        steps=[AnalysisStep(code="compare", title="Сопоставление", status="processing")],
        summary=AnalysisSummary(before_functions=1, lost=1),
        findings=[Finding(id="F1", type="lost", severity="medium", title="Потенциальная потеря",
                          explanation="Пара не найдена", confidence=0.8, before=evidence,
                          recommendation="Проверить закрепление функции")],
        conclusion="Сохранённое заключение", warnings=["Требуется проверка специалиста"],
        quality_score=0.8,
        function_registry=FunctionRegistry(
            functions=[ExtractedFunction(id="B1", source_id="B1", side="before",
                                         action="Готовит отчёт", evidence=evidence)],
            source_reviews=[SourceReview(source_id="B1", side="before", document="регламент.docx",
                                         clause="1.2", status="functions")],
            mappings=[FunctionMapping(before_id="B1", after_ids=[], status="lost",
                                      explanation="Нет пары")],
            coverage=CoverageMetrics(total_fragments=1, reviewed_fragments=1, before_functions=1),
        ),
    )


@pytest.mark.asyncio
async def test_memory_snapshots_do_not_share_mutable_objects():
    store = MemoryAnalysisStore()
    original = snapshot()
    await store.put(original)
    original.findings.clear()
    fetched = await store.get(original.id)
    assert fetched and len(fetched.findings) == 1
    fetched.warnings.clear()
    assert (await store.get(original.id)).warnings
    assert await store.get("unknown") is None


@pytest.mark.asyncio
async def test_start_recovers_only_interrupted_runs():
    store = MemoryAnalysisStore()
    completed, failed, queued, processing = [snapshot(s) for s in (
        "completed", "failed", "queued", "processing"
    )]
    for item in (completed, failed, queued, processing):
        await store.put(item)
    assert await store.start() == 2
    assert await store.get(completed.id) == completed
    assert await store.get(failed.id) == failed
    for item in (queued, processing):
        recovered = await store.get(item.id)
        assert recovered.status == AnalysisStatus.FAILED
        assert recovered.error.code == "ANALYSIS_INTERRUPTED"
        assert recovered.progress == 35
        assert recovered.steps[0].status == StepStatus.FAILED
        assert recovered.function_registry == item.function_registry
    assert await store.start() == 0


@pytest.mark.asyncio
async def test_database_required_no_silent_memory_fallback():
    store = PostgresAnalysisStore("")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        await store.start()
    with pytest.raises(ConnectionError):
        await store.healthy()


@pytest_asyncio.fixture
async def postgres_schema():
    dsn = os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Set TEST_DATABASE_URL to run real PostgreSQL integration tests")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://", 1)
    connection = await asyncpg.connect(dsn)
    schema = f"test_ai_first_{uuid4().hex}"
    # Fresh test-owned schema; never clear production tables or caller-owned schemas.
    await connection.execute(f'CREATE SCHEMA "{schema}"')
    try:
        yield dsn, schema
    finally:
        await connection.execute(f'DROP SCHEMA "{schema}" CASCADE')
        await connection.close()


@pytest.mark.asyncio
async def test_postgres_reopen_preserves_complete_result_and_recovers_jobs(postgres_schema):
    dsn, schema = postgres_schema
    first = PostgresAnalysisStore(dsn, schema=schema)
    completed, queued, processing = [snapshot(s) for s in ("completed", "queued", "processing")]
    assert await first.start() == 0
    try:
        for item in (completed, queued, processing):
            await first.put(item)
        # Exercise upsert and a parameterized lookup with hostile-looking input.
        completed.title = "Обновлённое название"
        await first.put(completed)
        assert await first.get("' OR 1=1 --") is None
        assert await first.healthy()
    finally:
        await first.close()
    second = PostgresAnalysisStore(dsn, schema=schema)
    assert await second.start() == 2
    try:
        assert await second.get(completed.id) == completed
        for previous in (queued, processing):
            recovered = await second.get(previous.id)
            assert recovered.status == AnalysisStatus.FAILED
            assert recovered.error.code == "ANALYSIS_INTERRUPTED"
            assert recovered.function_registry == previous.function_registry
        result = await second.get(completed.id)
        result.findings.clear()
        assert len((await second.get(completed.id)).findings) == 1
    finally:
        await second.close()


@pytest.mark.asyncio
async def test_second_worker_cannot_invalidate_active_run(postgres_schema):
    dsn, schema = postgres_schema
    owner = PostgresAnalysisStore(dsn, schema=schema)
    other = PostgresAnalysisStore(dsn, schema=schema)
    await owner.start()
    processing = snapshot("processing")
    try:
        await owner.put(processing)
        with pytest.raises(RuntimeError, match="one backend worker"):
            await other.start()
        assert (await owner.get(processing.id)).status == AnalysisStatus.PROCESSING
    finally:
        await owner.close()
        await other.close()


@pytest.mark.asyncio
async def test_lost_worker_lock_fails_closed(postgres_schema):
    dsn, schema = postgres_schema
    store = PostgresAnalysisStore(dsn, schema=schema)
    await store.start()
    try:
        store._guard.terminate()
        with pytest.raises(ConnectionError):
            await store.healthy()
        with pytest.raises(ConnectionError):
            await store.put(snapshot())
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_api_result_survives_application_restart(postgres_schema, monkeypatch):
    from app import main

    dsn, schema = postgres_schema
    store = PostgresAnalysisStore(dsn, schema=schema)
    monkeypatch.setattr(main, "store", store)
    completed = snapshot()
    queued = snapshot("queued")
    with TestClient(main.app) as client:
        client.portal.call(store.put, completed)
        client.portal.call(store.put, queued)
        before = client.get(f"/api/v1/analyses/{completed.id}")
        assert before.status_code == 200
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
        after = client.get(f"/api/v1/analyses/{completed.id}")
        assert before.json() == after.json()
        interrupted = client.get(f"/api/v1/analyses/{queued.id}").json()
        assert interrupted["status"] == "failed"
        assert interrupted["error"]["code"] == "ANALYSIS_INTERRUPTED"
