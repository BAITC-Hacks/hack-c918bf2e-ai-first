import time
from io import BytesIO

from docx import Document
from fastapi.testclient import TestClient

from app import main, pipeline
from app.analyzer import ComparisonDraft, EvidenceDraft, FindingDraft, QualityAssessment
from app.config import Settings
from app.main import app
from app.registry import FunctionLinkDraft

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
        assert result["summary"]["changed"] == 1
        assert result["findings"][0]["before"]["quote"] == "ежемесячный отчёт"
        assert "before.docx, 2.1" in result["conclusion"]
        assert result["agent_trace"]
        assert result["function_registry"]["coverage"]["matched_before_functions"] == 1
        assert result["function_registry"]["coverage"]["reviewed_fragments"] == 2
        assert all(step["status"] == "completed" for step in result["steps"])
