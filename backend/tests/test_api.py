import asyncio
import threading
import time
from datetime import UTC, datetime
from io import BytesIO

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app import main, pipeline
from app.analyzer import ComparisonDraft, EvidenceDraft, FindingDraft, QualityAssessment
from app.config import Settings
from app.main import app
from app.registry import FunctionLinkDraft
from app.schemas import AgentTraceEntry, Analysis, AnalysisStep, FunctionRegistry
from app.store import MemoryAnalysisStore

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch):
    monkeypatch.setattr(main, "store", MemoryAnalysisStore())


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_fails_when_storage_unavailable(monkeypatch) -> None:
    async def unavailable():
        raise ConnectionError("private database connection info")

    monkeypatch.setattr(main.store, "healthy", unavailable)
    response = client.get("/health")
    assert response.status_code == 503
    assert "private" not in response.text


def test_storage_errors_are_sanitized(monkeypatch) -> None:
    async def unavailable(*args):
        raise ConnectionError("private database password")

    monkeypatch.setattr(main.store, "get", unavailable)
    response = client.get("/api/v1/analyses/unknown")
    assert response.status_code == 503
    assert "private" not in response.text


def test_missing_analysis_returns_404() -> None:
    assert client.get("/api/v1/analyses/unknown").status_code == 404


@pytest.mark.asyncio
async def test_cancelled_job_preserves_interrupted_state(monkeypatch):
    started = asyncio.Event()

    async def blocked_worker(*args):
        started.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(main.asyncio, "to_thread", blocked_worker)
    analysis = Analysis(id="cancelled-test", title="Test", status="queued", progress=20,
                        current_step="Выделение функций", created_at=datetime.now(UTC),
                        steps=[AnalysisStep(code="structure", title="Функции", status="processing")])
    await main.store.put(analysis)
    task = asyncio.create_task(main.run_analysis(analysis.id, [], []))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    recovered = await main.store.get(analysis.id)
    assert recovered.status == "failed"
    assert recovered.progress == 20
    assert recovered.error.code == "ANALYSIS_INTERRUPTED"
    assert recovered.steps[0].status == "failed"


def test_api_exposes_live_checkpoint_and_keeps_it_on_provider_failure(monkeypatch, tmp_path):
    ready, finish = threading.Event(), threading.Event()

    def worker(before, after, settings, on_stage, on_checkpoint):
        on_stage("structure", 20)
        on_checkpoint([
            AgentTraceEntry(agent="document_tools", action="extract", status="completed",
                            summary="Тестовый завершённый шаг")
        ], FunctionRegistry())
        ready.set()
        finish.wait(timeout=3)
        raise RuntimeError("private-provider-error-must-not-leak")

    monkeypatch.setattr(main, "analyze_documents", worker)
    monkeypatch.setattr(main, "settings", Settings(upload_dir=str(tmp_path)))
    with TestClient(app) as session:
        created = session.post("/api/v1/analyses", files=[
            ("before_files", ("before.docx", b"stubbed-parser")),
            ("after_files", ("after.docx", b"stubbed-parser")),
        ])
        assert created.status_code == 202
        try:
            assert ready.wait(timeout=2)
            url = f"/api/v1/analyses/{created.json()['id']}"
            running = session.get(url).json()
            assert running["status"] == "processing"
            assert running["agent_trace"][0]["action"] == "extract"
            assert running["function_registry"] is not None
        finally:
            finish.set()
        for _ in range(100):
            result = session.get(url).json()
            if result["status"] == "failed":
                break
            time.sleep(0.01)
        assert result["status"] == "failed"
        assert result["agent_trace"] == running["agent_trace"]
        assert result["function_registry"] == running["function_registry"]
        assert "private-provider-error" not in result["error"]["message"]


def test_analysis_requires_supported_documents() -> None:
    response = client.post(
        "/api/v1/analyses",
        files=[
            ("before_files", ("before.txt", BytesIO(b"before"), "text/plain")),
            ("after_files", ("after.txt", BytesIO(b"after"), "text/plain")),
        ],
    )
    assert response.status_code == 415


def test_upload_to_completed_report_with_stubbed_provider(
    tmp_path, monkeypatch, stub_registry_model
) -> None:
    """Real upload/parser/orchestrator/store/API; only external model calls are stubbed."""
    monkeypatch.setattr(
        main,
        "settings",
        Settings(upload_dir=str(tmp_path), openai_api_key="test", agent_max_revisions=0),
    )
    comparison = ComparisonDraft(
        before_function_count=1,
        after_function_count=1,
        organization_changes=[],
        findings=[
            FindingDraft(
                type="changed",
                severity="medium",
                title="Изменение периодичности",
                explanation="Срок подготовки отчёта изменён с месяца на квартал.",
                confidence=0.9,
                before=EvidenceDraft(
                    document="before.docx", clause="2.1", quote="ежемесячный отчёт"
                ),
                after=EvidenceDraft(
                    document="after.docx", clause="4.2", quote="ежеквартальный отчёт"
                ),
                recommendation="Согласовать периодичность контроля.",
            )
        ],
        conclusion="Черновик",
        function_links=[
            FunctionLinkDraft(
                before_id="B0001-F01",
                after_ids=["A0001-F01"],
                status="changed",
                explanation="Изменена периодичность",
            )
        ],
    )
    monkeypatch.setattr(pipeline, "analyze_with_openai", lambda *args: comparison)
    monkeypatch.setattr(
        pipeline,
        "assess_quality_with_openai",
        lambda *args: QualityAssessment(passed=True, score=0.9, issues=[], summary="Проверено"),
    )
    files = []
    for side, text in (
        ("before", "2.1. Готовит ежемесячный отчёт"),
        ("after", "4.2. Готовит ежеквартальный отчёт"),
    ):
        document = Document()
        document.add_paragraph(text)
        buffer = BytesIO()
        document.save(buffer)
        files.append(
            (
                f"{side}_files",
                (
                    f"{side}.docx",
                    buffer.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            )
        )
    with TestClient(app) as session:
        response = session.post("/api/v1/analyses", files=files)
        assert response.status_code == 202
        for _ in range(100):
            result = session.get(f"/api/v1/analyses/{response.json()['id']}").json()
            if result["status"] in {"completed", "failed"}:
                break
            time.sleep(0.01)
        assert result["status"] == "completed", result
        assert result["structural_risks"] == []
        assert result["summary"]["changed"] == 1
        assert result["findings"][0]["before"]["quote"] == "ежемесячный отчёт"
        assert "before.docx, 2.1" in result["conclusion"]
        assert result["agent_trace"]
        assert result["function_registry"]["coverage"]["matched_before_functions"] == 1
        assert result["function_registry"]["coverage"]["reviewed_fragments"] == 2
        assert all(step["status"] == "completed" for step in result["steps"])
