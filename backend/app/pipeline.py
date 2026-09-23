import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.analyzer import (
    ComparisonDraft,
    EvidenceDraft,
    analyze_with_openai,
    assess_quality_with_openai,
    revise_with_openai,
)
from app.config import Settings
from app.documents import Clause, parse_documents
from app.schemas import (
    AnalysisSummary,
    Evidence,
    Finding,
    FindingType,
    OrganizationChange,
    OrganizationChangeStatus,
    Severity,
    AgentTraceEntry,
)


@dataclass
class PipelineResult:
    summary: AnalysisSummary
    findings: list[Finding]
    organization_changes: list[OrganizationChange]
    conclusion: str
    warnings: list[str]
    agent_trace: list[AgentTraceEntry]
    quality_score: float


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower().replace("ё", "е")


def normalize_clause(value: str) -> str:
    match = re.search(r"\d+(?:\.\d+)+", value)
    return match.group(0) if match else value.strip().rstrip(".")


def evidence_index(clauses: list[Clause]) -> dict[tuple[str, str], Clause]:
    return {(normalize(item.document), normalize_clause(item.clause)): item for item in clauses}


def verify_evidence(
    draft: EvidenceDraft | None, index: dict[tuple[str, str], Clause]
) -> Evidence | None:
    if draft is None:
        return None
    clause_number = normalize_clause(draft.clause)
    clause = index.get((normalize(draft.document), clause_number))
    if clause is None:
        same_number = [item for (_, number), item in index.items() if number == clause_number]
        clause = same_number[0] if len(same_number) == 1 else None
    if clause is None:
        return None
    # The model selects the source clause; the quote itself always comes from the
    # parser. This prevents a paraphrased or hallucinated quote from reaching users.
    exact_quote = clause.text[:1200]
    return Evidence(
        department=draft.department,
        clause=clause.clause,
        quote=exact_quote,
        document=clause.document,
        page=clause.page,
    )


def required_evidence_present(kind: FindingType, before: Evidence | None, after: Evidence | None) -> bool:
    if kind == FindingType.LOST:
        return before is not None
    if kind == FindingType.ADDED:
        return after is not None
    return before is not None and after is not None


def build_findings(
    comparison: ComparisonDraft, before_clauses: list[Clause], after_clauses: list[Clause]
) -> tuple[list[Finding], list[str]]:
    before_index = evidence_index(before_clauses)
    after_index = evidence_index(after_clauses)
    findings: list[Finding] = []
    rejected = 0
    for draft in comparison.findings:
        before = verify_evidence(draft.before, before_index)
        after = verify_evidence(draft.after, after_index)
        if not required_evidence_present(draft.type, before, after):
            rejected += 1
            continue
        findings.append(
            Finding(
                id=str(uuid4()),
                type=draft.type,
                severity=draft.severity,
                title=draft.title,
                explanation=draft.explanation,
                confidence=draft.confidence,
                before=before,
                after=after,
                recommendation=draft.recommendation,
            )
        )
    warnings = []
    if rejected:
        warnings.append(f"Контроль качества исключил выводы без проверяемых цитат: {rejected}.")
    return findings, warnings


def make_summary(before: list[Clause], after: list[Clause], findings: list[Finding]) -> AnalysisSummary:
    counts = {kind: 0 for kind in FindingType}
    for finding in findings:
        counts[finding.type] += 1
    return AnalysisSummary(
        before_functions=len(before),
        after_functions=len(after),
        unchanged=max(0, min(len(before), len(after)) - sum(counts.values())),
        lost=counts[FindingType.LOST],
        added=counts[FindingType.ADDED],
        moved=counts[FindingType.MOVED],
        changed=counts[FindingType.CHANGED],
        duplicates=counts[FindingType.DUPLICATE],
        high_risk=sum(item.severity == Severity.HIGH for item in findings),
    )


def build_organization_changes(
    comparison: ComparisonDraft, before_clauses: list[Clause], after_clauses: list[Clause]
) -> tuple[list[OrganizationChange], int]:
    before_index = evidence_index(before_clauses)
    after_index = evidence_index(after_clauses)
    changes: list[OrganizationChange] = []
    rejected = 0
    for draft in comparison.organization_changes:
        before = verify_evidence(draft.before, before_index)
        after = verify_evidence(draft.after, after_index)
        if draft.status == OrganizationChangeStatus.CREATED:
            before = None
        elif draft.status == OrganizationChangeStatus.REMOVED:
            after = None
        valid = {
            OrganizationChangeStatus.CREATED: after is not None,
            OrganizationChangeStatus.REMOVED: before is not None,
            OrganizationChangeStatus.PRESERVED: before is not None and after is not None,
            OrganizationChangeStatus.TRANSFORMED: before is not None and after is not None,
        }[draft.status]
        if not valid:
            rejected += 1
            continue
        changes.append(
            OrganizationChange(
                id=str(uuid4()),
                status=draft.status,
                before_name=draft.before_name,
                after_name=draft.after_name,
                explanation=draft.explanation,
                before=before,
                after=after,
            )
        )
    return changes, rejected


def analyze_documents(before: list[Path], after: list[Path], settings: Settings) -> PipelineResult:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY не настроен")
    trace = [
        AgentTraceEntry(
            agent="orchestrator",
            action="plan",
            status="completed",
            summary=(
                f"Выбрана стратегия полного сопоставления: документов до — {len(before)}, "
                f"после — {len(after)}."
            ),
        )
    ]
    before_clauses = parse_documents(before)
    after_clauses = parse_documents(after)
    if not before_clauses or not after_clauses:
        raise RuntimeError("Не удалось выделить нумерованные пункты в одном из комплектов")
    trace.append(
        AgentTraceEntry(
            agent="document_tools",
            action="extract",
            status="completed",
            summary=f"Извлечено пунктов: до — {len(before_clauses)}, после — {len(after_clauses)}.",
        )
    )
    comparison = analyze_with_openai(before_clauses, after_clauses, settings)
    trace.append(
        AgentTraceEntry(
            agent="comparison_agent",
            action="compare",
            status="completed",
            summary=(
                f"Первичный анализ: изменений структуры — {len(comparison.organization_changes)}, "
                f"функциональных отклонений — {len(comparison.findings)}."
            ),
        )
    )

    assessment = assess_quality_with_openai(comparison, settings)
    trace.append(
        AgentTraceEntry(
            agent="critic_agent",
            action="evaluate",
            status="completed",
            summary=f"Оценка качества: {assessment.score:.0%}. {assessment.summary}",
        )
    )
    revisions = 0
    while (
        revisions < settings.agent_max_revisions
        and (not assessment.passed or assessment.score < settings.agent_quality_threshold)
        and assessment.issues
    ):
        candidate = revise_with_openai(
            before_clauses, after_clauses, comparison, assessment, settings
        )
        revisions += 1
        trace.append(
            AgentTraceEntry(
                agent="comparison_agent",
                action="revise",
                status="completed",
                summary=f"Выполнено целевое исправление по замечаниям контролёра: {revisions}.",
            )
        )
        candidate_assessment = assess_quality_with_openai(candidate, settings)
        trace.append(
            AgentTraceEntry(
                agent="critic_agent",
                action="re-evaluate",
                status="completed",
                summary=(
                    f"Повторная оценка качества: {candidate_assessment.score:.0%}. "
                    f"{candidate_assessment.summary}"
                ),
            )
        )
        if candidate_assessment.score >= assessment.score:
            comparison = candidate
            assessment = candidate_assessment
            trace.append(
                AgentTraceEntry(
                    agent="orchestrator",
                    action="accept_revision",
                    status="completed",
                    summary="Исправленная версия принята: оценка качества не снизилась.",
                )
            )
        else:
            trace.append(
                AgentTraceEntry(
                    agent="orchestrator",
                    action="rollback",
                    status="completed",
                    summary=(
                        "Исправленная версия отклонена: orchestrator сохранил вариант "
                        f"с более высокой оценкой {assessment.score:.0%}."
                    ),
                )
            )
            break
    findings, warnings = build_findings(comparison, before_clauses, after_clauses)
    if assessment.score < settings.agent_quality_threshold:
        warnings.append(
            f"Оценка контролёра {assessment.score:.0%}: результат требует проверки специалистом."
        )
    organization_changes, rejected_organizations = build_organization_changes(
        comparison, before_clauses, after_clauses
    )
    if rejected_organizations:
        warnings.append(
            "Контроль качества исключил изменения структуры без проверяемых цитат: "
            f"{rejected_organizations}."
        )
    trace.append(
        AgentTraceEntry(
            agent="evidence_verifier",
            action="verify",
            status="completed",
            summary=(
                f"Проверены источники: принято {len(findings)} выводов и "
                f"{len(organization_changes)} изменений структуры."
            ),
        )
    )
    summary = make_summary(before_clauses, after_clauses, findings)
    summary.before_functions = comparison.before_function_count
    summary.after_functions = comparison.after_function_count
    summary.unchanged = max(
        0,
        min(comparison.before_function_count, comparison.after_function_count)
        - len(findings),
    )
    return PipelineResult(
        summary=summary,
        findings=findings,
        organization_changes=organization_changes,
        conclusion=comparison.conclusion,
        warnings=warnings,
        agent_trace=trace,
        quality_score=assessment.score,
    )
