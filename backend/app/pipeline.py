import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.analyzer import (
    ComparisonDraft,
    EvidenceDraft,
    QualityAssessment,
    QualityIssue,
    analyze_with_openai,
    assess_quality_with_openai,
    revise_with_openai,
)
from app.config import Settings
from app.documents import Clause, parse_documents
from app.schemas import (
    AgentTraceEntry,
    AnalysisSummary,
    Evidence,
    Finding,
    FindingType,
    OrganizationChange,
    OrganizationChangeStatus,
    Severity,
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
    match = re.fullmatch(r"\s*(?:п(?:ункт)?\.?\s*)?(\d+(?:\.\d+)*)(?:[.)])?\s*", value)
    return match.group(1) if match else normalize(value)


def evidence_index(clauses: list[Clause]) -> dict[tuple[str, str], list[Clause]]:
    index: dict[tuple[str, str], list[Clause]] = {}
    for item in clauses:
        index.setdefault((normalize(item.document), normalize_clause(item.clause)), []).append(item)
    return index


def verify_evidence(
    draft: EvidenceDraft | None, index: dict[tuple[str, str], list[Clause]]
) -> Evidence | None:
    if draft is None:
        return None
    clause_number = normalize_clause(draft.clause)
    candidates = index.get((normalize(draft.document), clause_number), [])
    # Never guess the document from a clause number. Ambiguous locators fail closed.
    if len(candidates) != 1 or not draft.quote.strip():
        return None
    clause = candidates[0]
    pattern = r"\s+".join(re.escape(word) for word in draft.quote.split())
    match = re.search(pattern, clause.text, re.IGNORECASE)
    if match is None:
        return None
    exact_quote = clause.text[match.start() : match.end()]
    return Evidence(
        department=draft.department,
        clause=clause.clause,
        quote=exact_quote,
        document=clause.document,
        page=clause.page,
    )


def required_evidence_present(
    kind: FindingType, before: Evidence | None, after: Evidence | None
) -> bool:
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
        if (
            (draft.before is not None and before is None)
            or (draft.after is not None and after is None)
            or not required_evidence_present(draft.type, before, after)
        ):
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


def make_summary(
    before: list[Clause], after: list[Clause], findings: list[Finding]
) -> AnalysisSummary:
    counts = {kind: 0 for kind in FindingType}
    for finding in findings:
        counts[finding.type] += 1
    return AnalysisSummary(
        before_functions=len(before),
        after_functions=len(after),
        unchanged=counts[FindingType.UNCHANGED],
        lost=counts[FindingType.LOST],
        added=counts[FindingType.ADDED],
        moved=counts[FindingType.MOVED],
        changed=counts[FindingType.CHANGED],
        duplicates=counts[FindingType.DUPLICATE],
        high_risk=sum(
            item.severity == Severity.HIGH and item.type != FindingType.UNCHANGED
            for item in findings
        ),
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
        if (draft.before is not None and before is None) or (
            draft.after is not None and after is None
        ):
            rejected += 1
            continue
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


def source_issues(
    comparison: ComparisonDraft, before: list[Clause], after: list[Clause]
) -> list[QualityIssue]:
    """Deterministic checks run before the LLM judge and cannot be overruled by it."""
    indexes = {"before": evidence_index(before), "after": evidence_index(after)}
    issues = []
    for category, items in (
        ("findings", comparison.findings),
        ("organization_changes", comparison.organization_changes),
    ):
        for position, item in enumerate(items):
            for side in ("before", "after"):
                evidence = getattr(item, side)
                if evidence is not None and verify_evidence(evidence, indexes[side]) is None:
                    issues.append(
                        QualityIssue(
                            category="invalid_source",
                            message=f"{category}[{position}].{side}: источник или цитата не подтверждены",
                            revision_instruction=(
                                f"Исправь {category}[{position}].{side}: скопируй точное имя документа, "
                                "обозначение фрагмента и непрерывную дословную цитату из источника. "
                                "Если подтверждения нет, удали вывод, не подбирай формальную ссылку."
                            ),
                        )
                    )
    findings, _ = build_findings(comparison, before, after)
    _, rejected_orgs = build_organization_changes(comparison, before, after)
    if len(findings) < len(comparison.findings) or rejected_orgs:
        issues.append(
            QualityIssue(
                category="missing_evidence",
                message="Часть выводов не проходит обязательную проверку доказательств",
                revision_instruction="Проверь наличие обязательных источников для каждого типа вывода.",
            )
        )
    return issues


def evaluate_comparison(
    comparison: ComparisonDraft, before: list[Clause], after: list[Clause], settings: Settings
) -> QualityAssessment:
    issues = source_issues(comparison, before, after)
    assessment = assess_quality_with_openai(comparison, settings, before, after, issues)
    if issues:
        assessment.passed = False
        assessment.score = min(assessment.score, 0.49)
        assessment.issues = issues + assessment.issues
    return assessment


def build_conclusion(
    findings: list[Finding], organizations: list[OrganizationChange], warnings: list[str]
) -> str:
    """No new model claims after filtering: report only accepted, source-linked items."""
    deviations = [item for item in findings if item.type != FindingType.UNCHANGED]
    lines = [
        "Предварительное заключение по представленным документам.",
        (
            f"Отклонений с проверяемыми цитатами: {len(deviations)}; "
            f"записей об организационной структуре: {len(organizations)}."
        ),
    ]
    for item in deviations:
        sources = "; ".join(
            f"{side}: {evidence.document}, {evidence.clause}"
            for side, evidence in (("ДО", item.before), ("ПОСЛЕ", item.after))
            if evidence is not None
        )
        lines.append(
            f"- {item.title}: {item.explanation} [{sources}] Рекомендация: {item.recommendation}"
        )
    for item in organizations:
        sources = "; ".join(
            f"{evidence.document}, {evidence.clause}"
            for evidence in (item.before, item.after)
            if evidence is not None
        )
        lines.append(f"- Структура ({item.status.value}): {item.explanation} [{sources}]")
    if not deviations:
        lines.append(
            "Отсутствие принятых отклонений не доказывает отсутствие рисков или потерь функций."
        )
    lines.append("Выводы и полноту сопоставления должен подтвердить ответственный специалист.")
    lines.extend(f"Ограничение: {warning}" for warning in warnings)
    return "\n\n".join(lines)


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
        raise RuntimeError("Не удалось извлечь текстовые фрагменты в одном из комплектов")
    trace.append(
        AgentTraceEntry(
            agent="document_tools",
            action="extract",
            status="completed",
            summary=f"Извлечено фрагментов: до — {len(before_clauses)}, после — {len(after_clauses)}.",
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

    initial_source_issues = source_issues(comparison, before_clauses, after_clauses)
    trace.append(
        AgentTraceEntry(
            agent="evidence_verifier",
            action="precheck",
            status="completed",
            summary=(
                "До модельной оценки проверены документы, локаторы и дословные цитаты; "
                f"замечаний: {len(initial_source_issues)}."
            ),
        )
    )
    assessment = evaluate_comparison(comparison, before_clauses, after_clauses, settings)
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
        candidate_assessment = evaluate_comparison(
            candidate, before_clauses, after_clauses, settings
        )
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
        source_errors = len(source_issues(comparison, before_clauses, after_clauses))
        candidate_errors = len(source_issues(candidate, before_clauses, after_clauses))
        if candidate_errors < source_errors or (
            candidate_errors == source_errors and candidate_assessment.score >= assessment.score
        ):
            comparison = candidate
            assessment = candidate_assessment
            trace.append(
                AgentTraceEntry(
                    agent="orchestrator",
                    action="accept_revision",
                    status="completed",
                    summary="Исправленная версия принята с приоритетом проверяемости источников.",
                )
            )
        else:
            trace.append(
                AgentTraceEntry(
                    agent="orchestrator",
                    action="rollback",
                    status="completed",
                    summary=(
                        "Исправленная версия отклонена: ухудшилась проверяемость источников "
                        "или, при равном числе ошибок, модельная оценка."
                    ),
                )
            )
            break
    findings, warnings = build_findings(comparison, before_clauses, after_clauses)
    if not assessment.passed or assessment.score < settings.agent_quality_threshold:
        warnings.append(
            f"Оценка контролёра {assessment.score:.0%}: результат требует проверки специалистом."
        )
        warnings.extend(issue.message for issue in assessment.issues)
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
    warnings.append(
        "Количество функций ДО/ПОСЛЕ — оценка модели, а не полный реестр. "
        "Без изменений — только явно сопоставленные пары; полнота покрытия не измерена. "
        "Оценка контролёра не является измеренной точностью системы."
    )
    return PipelineResult(
        summary=summary,
        findings=findings,
        organization_changes=organization_changes,
        conclusion=build_conclusion(findings, organization_changes, warnings),
        warnings=warnings,
        agent_trace=trace,
        quality_score=assessment.score,
    )
