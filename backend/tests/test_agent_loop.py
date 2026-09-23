from pathlib import Path

import pytest
from docx import Document

from app import pipeline
from app.analyzer import ComparisonDraft, EvidenceDraft, FindingDraft, QualityAssessment
from app.config import Settings
from app.documents import Clause
from app.registry import FunctionLinkDraft
from app.schemas import FindingType, Severity


def draft(quote: str = "Контролирует риски") -> ComparisonDraft:
    return ComparisonDraft(
        before_function_count=5,
        after_function_count=4,
        organization_changes=[],
        findings=[
            FindingDraft(
                type=FindingType.LOST,
                severity=Severity.HIGH,
                title="Потеря контроля",
                explanation="В переданном комплекте не найден контроль рисков.",
                confidence=0.8,
                before=EvidenceDraft(document="before.docx", clause="1.1", quote=quote),
                after=None,
                recommendation="Проверить закрепление функции.",
            )
        ],
        conclusion="НЕПРОВЕРЕННОЕ УТВЕРЖДЕНИЕ",
        function_links=[
            FunctionLinkDraft(
                before_id="B0001-F01",
                after_ids=[],
                status="lost",
                explanation="Не найдена в новом комплекте",
            )
        ],
        added_after_ids=["A0001-F01"],
    )


def assessment() -> QualityAssessment:
    return QualityAssessment(passed=True, score=0.95, issues=[], summary="Проверено")


def documents(tmp_path: Path) -> tuple[list[Path], list[Path]]:
    paths = []
    for filename, text in (
        ("before.docx", "1.1. Контролирует риски"),
        ("after.docx", "1.1. Формирует отчётность"),
    ):
        document = Document()
        document.add_paragraph(text)
        path = tmp_path / filename
        document.save(path)
        paths.append(path)
    return [paths[0]], [paths[1]]


def test_judge_cannot_overrule_invalid_quote(monkeypatch) -> None:
    calls = []

    def critic(comparison, settings, before, after, issues, registry=None):
        calls.append((before, after, issues))
        return assessment()

    monkeypatch.setattr(pipeline, "assess_quality_with_openai", critic)
    before = [Clause("before.docx", "1.1", "Контролирует риски")]
    after = [Clause("after.docx", "1.1", "Формирует отчётность")]
    result = pipeline.evaluate_comparison(draft("Выдуманная цитата"), before, after, Settings())
    assert result.passed is False
    assert result.score <= 0.49
    assert calls[0][0] == before and calls[0][1] == after
    assert calls[0][2]


def test_full_pipeline_repairs_invalid_quote_and_reports_only_accepted_claims(
    tmp_path, monkeypatch, stub_registry_model
):
    before, after = documents(tmp_path)
    monkeypatch.setattr(pipeline, "analyze_with_openai", lambda *args: draft("Выдумка"))
    monkeypatch.setattr(pipeline, "assess_quality_with_openai", lambda *args: assessment())
    revisions = []

    def revise(*args):
        revisions.append(args)
        return draft()

    monkeypatch.setattr(pipeline, "revise_with_openai", revise)
    result = pipeline.analyze_documents(before, after, Settings(openai_api_key="test"))
    assert len(revisions) == 1
    assert len(result.findings) == 1
    assert "НЕПРОВЕРЕННОЕ" not in result.conclusion
    assert "before.docx, 1.1" in result.conclusion
    assert result.summary.unchanged == 0
    assert any(item.action == "accept_revision" for item in result.agent_trace)


def test_exhausted_repair_drops_claim_from_report(tmp_path, monkeypatch, stub_registry_model):
    before, after = documents(tmp_path)
    monkeypatch.setattr(pipeline, "analyze_with_openai", lambda *args: draft("Выдумка"))
    monkeypatch.setattr(pipeline, "assess_quality_with_openai", lambda *args: assessment())
    result = pipeline.analyze_documents(
        before, after, Settings(openai_api_key="test", agent_max_revisions=0)
    )
    assert result.findings == []
    assert "Потеря контроля" not in result.conclusion
    assert "НЕПРОВЕРЕННОЕ" not in result.conclusion
    assert result.warnings


@pytest.mark.parametrize("revisions", [-1, 3])
def test_revision_budget_is_bounded(revisions):
    with pytest.raises(ValueError):
        Settings(agent_max_revisions=revisions)
