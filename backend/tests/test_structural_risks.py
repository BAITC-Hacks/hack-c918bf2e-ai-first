from datetime import UTC, datetime

import pytest

from app import pipeline
from app.analyzer import (
    ComparisonDraft,
    EvidenceDraft,
    FindingDraft,
    QualityAssessment,
    RiskEvidenceDraft,
    StructuralRiskDraft,
)
from app.config import Settings
from app.documents import Clause
from app.schemas import Analysis

AFTER = [
    Clause("after.docx", "3.1", "Отдел закупок проводит закупки оборудования."),
    Clause("after.docx", "3.2", "Отдел закупок независимо проверяет собственные закупки оборудования."),
]


def comparison(kind="conflict_interest"):
    risk = StructuralRiskDraft(
        kind=kind, severity="high", title="Самопроверка закупок",
        explanation="Одному исполнителю поручены исполнение и независимый контроль.",
        confidence=0.8, recommendation="Проверить разделение ролей.",
        evidence=[RiskEvidenceDraft(
            side="after", evidence=EvidenceDraft(document=c.document, clause=c.clause, quote=c.text)
        ) for c in AFTER],
    )
    return ComparisonDraft(before_function_count=0, after_function_count=2,
                           organization_changes=[], findings=[], structural_risks=[risk],
                           conclusion="Черновик")


@pytest.mark.parametrize("kind", ["duplicate", "conflict_interest"])
def test_risk_with_two_after_sources_is_accepted(kind):
    risks, warnings = pipeline.build_structural_risks(comparison(kind), [], AFTER)
    assert len(risks) == 1
    assert risks[0].kind == kind
    assert [e.side for e in risks[0].evidence] == ["after", "after"]
    assert [e.evidence.quote for e in risks[0].evidence] == [c.text for c in AFTER]
    assert warnings == []


def test_risk_in_before_is_not_relabelled_as_after():
    draft = comparison()
    for item in draft.structural_risks[0].evidence:
        item.side = "before"
    risks, _ = pipeline.build_structural_risks(draft, AFTER, [])
    assert len(risks) == 1
    assert all(item.side == "before" for item in risks[0].evidence)


def test_risk_cannot_use_opposite_versions_as_same_version_proof():
    draft = comparison()
    draft.structural_risks[0].evidence[0].side = "before"
    risks, warnings = pipeline.build_structural_risks(draft, AFTER, AFTER)
    assert not risks and warnings
    assert pipeline.source_issues(draft, AFTER, AFTER)


def test_repeated_locator_is_not_two_independent_sources():
    draft = comparison()
    evidence = draft.structural_risks[0].evidence[0]
    draft.structural_risks[0].evidence = [evidence, evidence.model_copy(deep=True)]
    risks, warnings = pipeline.build_structural_risks(draft, [], AFTER)
    assert not risks and warnings


@pytest.mark.parametrize("field,value", [("quote", "Выдуманная цитата"), ("document", "fake.docx")])
def test_one_invalid_source_excludes_entire_risk(field, value):
    draft = comparison()
    setattr(draft.structural_risks[0].evidence[1].evidence, field, value)
    risks, warnings = pipeline.build_structural_risks(draft, [], AFTER)
    assert not risks and warnings
    assert any(item.category == "invalid_source" for item in pipeline.source_issues(draft, [], AFTER))


def test_same_risk_sources_are_deduplicated():
    draft = comparison()
    draft.structural_risks.append(draft.structural_risks[0].model_copy(deep=True))
    draft.structural_risks[1].evidence.reverse()
    risks, _ = pipeline.build_structural_risks(draft, [], AFTER)
    assert len(risks) == 1


def test_legacy_before_after_duplicate_is_not_accepted():
    draft = comparison()
    draft.structural_risks = []
    evidence = EvidenceDraft(document="after.docx", clause="3.1", quote=AFTER[0].text)
    draft.findings = [FindingDraft(type="duplicate", severity="high", title="Ложный дубль",
                                  explanation="Та же функция до и после", confidence=0.9,
                                  before=evidence, after=evidence, recommendation="Проверить")]
    findings, warnings = pipeline.build_findings(draft, AFTER, AFTER)
    assert findings == [] and warnings


def test_conclusion_contains_kind_and_all_source_sides():
    risks, _ = pipeline.build_structural_risks(comparison(), [], AFTER)
    conclusion = pipeline.build_conclusion([], [], [], risks)
    assert "Потенциальный риск (конфликт интересов)" in conclusion
    assert "ПОСЛЕ: after.docx, 3.1" in conclusion
    assert "ПОСЛЕ: after.docx, 3.2" in conclusion
    assert "Отсутствие принятых отклонений" not in conclusion


def test_model_critic_cannot_accept_invalid_structural_risk(monkeypatch):
    draft = comparison()
    draft.structural_risks[0].evidence[0].evidence.quote = "Не существует"
    monkeypatch.setattr(pipeline, "assess_quality_with_openai", lambda *args: QualityAssessment(
        passed=True, score=0.99, issues=[], summary="Ошибочное одобрение"
    ))
    assessment = pipeline.evaluate_comparison(draft, [], AFTER, Settings())
    assert not assessment.passed
    assert assessment.score <= 0.49
    assert assessment.issues


def test_older_results_distinguish_unavailable_risks_from_empty_results():
    older = Analysis(id="old", title="Legacy", status="completed", progress=100,
                     current_step="Готово", created_at=datetime.now(UTC), steps=[])
    assert older.structural_risks is None
    newer = older.model_copy(update={"structural_risks": []})
    assert newer.structural_risks == []
