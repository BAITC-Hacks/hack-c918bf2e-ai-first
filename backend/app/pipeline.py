import re
from collections.abc import Callable
from dataclasses import dataclass, field
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
from app.documents import Clause, match_source_quote, parse_documents
from app.registry import FunctionLinkDraft, extract_registry, match_registry, reconcile_mappings
from app.schemas import (
    AgentTraceEntry,
    AnalysisSummary,
    Evidence,
    Finding,
    FindingType,
    FunctionRegistry,
    MappingStatus,
    OrganizationChange,
    OrganizationChangeStatus,
    RiskEvidence,
    Severity,
    StructuralRisk,
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
    function_registry: FunctionRegistry
    structural_risks: list[StructuralRisk] = field(default_factory=list)


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
    exact_quote = match_source_quote(draft.quote, clause.text)
    if exact_quote is None:
        return None
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
    if kind == FindingType.DUPLICATE:
        # A before/after pair cannot establish same-version duplication.
        return False
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


def build_structural_risks(
    comparison: ComparisonDraft, before_clauses: list[Clause], after_clauses: list[Clause]
) -> tuple[list[StructuralRisk], list[str]]:
    indexes = {"before": evidence_index(before_clauses), "after": evidence_index(after_clauses)}
    risks: list[StructuralRisk] = []
    rejected = 0
    seen = set()
    for draft in comparison.structural_risks:
        verified = []
        for item in draft.evidence:
            evidence = verify_evidence(item.evidence, indexes[item.side])
            if evidence is not None:
                verified.append(RiskEvidence(side=item.side, evidence=evidence))
        locators = {(item.side, item.evidence.document, item.evidence.clause) for item in verified}
        if (len(verified) != len(draft.evidence) or len(locators) < 2
                or len({item.side for item in verified}) != 1):
            rejected += 1
            continue
        key = (draft.kind, frozenset(locators))
        if key in seen:
            continue
        seen.add(key)
        risks.append(StructuralRisk(
            id=str(uuid4()), kind=draft.kind, severity=draft.severity, title=draft.title,
            explanation=draft.explanation, confidence=draft.confidence, evidence=verified,
            recommendation=draft.recommendation,
        ))
    warnings = []
    if rejected:
        warnings.append(
            f"Контроль качества исключил структурные риски: {rejected}. "
            "Нужны как минимум два разных подтверждённых фрагмента одной редакции."
        )
    return risks, warnings


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
    comparison: ComparisonDraft,
    before: list[Clause],
    after: list[Clause],
    registry: FunctionRegistry | None = None,
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
    for position, risk in enumerate(comparison.structural_risks):
        for number, item in enumerate(risk.evidence):
            if verify_evidence(item.evidence, indexes[item.side]) is None:
                issues.append(QualityIssue(
                    category="invalid_source",
                    message=f"structural_risks[{position}].evidence[{number}]: цитата не подтверждена",
                    revision_instruction="Укажи точный фрагмент и дословную цитату указанной редакции. "
                    "Если подтверждения нет, удали структурный риск.",
                ))
    risks, _ = build_structural_risks(comparison, before, after)
    if len(risks) < len(comparison.structural_risks):
        issues.append(QualityIssue(
            category="missing_evidence",
            message="Структурные риски содержат повторные/невалидные или межредакционные основания",
            revision_instruction="Для каждого structural_risks нужны два разных фрагмента одной "
            "редакции. Не повторяй риски с одинаковыми основаниями. Если оснований нет, удали риск.",
        ))
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
    if registry is not None:
        reconciled = reconcile_mappings(
            registry, comparison.function_links, comparison.added_after_ids
        )
        before_ids = {item.id for item in registry.functions if item.side == "before"}
        after_ids = {item.id for item in registry.functions if item.side == "after"}
        invalid_ids = any(
            item.before_id not in before_ids
            or any(target not in after_ids for target in item.after_ids)
            for item in comparison.function_links
        ) or any(item not in after_ids for item in comparison.added_after_ids)
        if reconciled.coverage.needs_review_mappings or invalid_ids:
            issues.append(
                QualityIssue(
                    category="coverage",
                    message=f"Требуют проверки сопоставления: {reconciled.coverage.needs_review_mappings}; "
                    f"невалидные ID: {'да' if invalid_ids else 'нет'}.",
                    revision_instruction=(
                        "Проверь все function_links и added_after_ids по реестру. "
                        "Дополни пропущенные пары; при реальной неопределённости "
                        "сохрани needs_review, не выдумывай подтверждение."
                    ),
                )
            )
    return issues


def evaluate_comparison(
    comparison: ComparisonDraft,
    before: list[Clause],
    after: list[Clause],
    settings: Settings,
    registry: FunctionRegistry | None = None,
) -> QualityAssessment:
    issues = source_issues(comparison, before, after, registry)
    # Review the report we actually publish, not unused free-form LLM prose.
    verified_findings, warnings = build_findings(comparison, before, after)
    verified_orgs, _ = build_organization_changes(comparison, before, after)
    verified_risks, risk_warnings = build_structural_risks(comparison, before, after)
    review_input = comparison.model_copy(update={
        "conclusion": build_conclusion(
            verified_findings, verified_orgs, warnings + risk_warnings, verified_risks
        )
    })
    review_registry = registry
    if registry is not None:
        # The critic must see the same guarded statuses that the API will publish,
        # not raw lost/added drafts already downgraded because extraction is incomplete.
        review_registry = reconcile_mappings(
            registry, comparison.function_links, comparison.added_after_ids
        )
        review_input.function_links = [
            FunctionLinkDraft(
                before_id=row.before_id, after_ids=row.after_ids,
                status=row.status.value, explanation=row.explanation,
            )
            for row in review_registry.mappings if row.before_id is not None
        ]
        review_input.added_after_ids = [
            item for row in review_registry.mappings
            if row.status == MappingStatus.ADDED for item in row.after_ids
        ]
    assessment = assess_quality_with_openai(
        review_input, settings, before, after, issues, review_registry
    )
    if issues:
        assessment.passed = False
        assessment.score = min(assessment.score, 0.49)
        assessment.issues = issues + assessment.issues
    return assessment


def build_conclusion(
    findings: list[Finding], organizations: list[OrganizationChange], warnings: list[str],
    structural_risks: list[StructuralRisk] | None = None,
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
    for risk in structural_risks or []:
        kind = "дублирование" if risk.kind == "duplicate" else "конфликт интересов"
        sources = "; ".join(
            f"{'ДО' if item.side == 'before' else 'ПОСЛЕ'}: "
            f"{item.evidence.document}, {item.evidence.clause}"
            for item in risk.evidence
        )
        lines.append(f"- Потенциальный риск ({kind}): {risk.title}. {risk.explanation} "
                     f"[{sources}] Рекомендация: {risk.recommendation}")
    for item in organizations:
        sources = "; ".join(
            f"{evidence.document}, {evidence.clause}"
            for evidence in (item.before, item.after)
            if evidence is not None
        )
        lines.append(f"- Структура ({item.status.value}): {item.explanation} [{sources}]")
    if not deviations and not structural_risks:
        lines.append(
            "Отсутствие принятых отклонений не доказывает отсутствие рисков или потерь функций."
        )
    lines.append("Выводы и полноту сопоставления должен подтвердить ответственный специалист.")
    lines.extend(f"Ограничение: {warning}" for warning in warnings)
    return "\n\n".join(lines)


def analyze_documents(
    before: list[Path],
    after: list[Path],
    settings: Settings,
    on_stage: Callable[[str, int], None] | None = None,
    on_checkpoint: Callable[[list[AgentTraceEntry], FunctionRegistry | None], None] | None = None,
) -> PipelineResult:
    registry: FunctionRegistry | None = None
    trace: list[AgentTraceEntry] = []

    def record(entry: AgentTraceEntry) -> None:
        trace.append(entry)
        if on_checkpoint:
            # Pass detached, validated snapshots; never expose model drafts or reasoning.
            on_checkpoint(
                [item.model_copy(deep=True) for item in trace],
                registry.model_copy(deep=True) if registry is not None else None,
            )

    def stage(code: str, progress: int) -> None:
        if on_stage:
            on_stage(code, progress)

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY не настроен")
    record(
        AgentTraceEntry(
            agent="orchestrator",
            action="plan",
            status="completed",
            summary=(
                f"Выбрана стратегия полного сопоставления: документов до — {len(before)}, "
                f"после — {len(after)}."
            ),
        )
    )
    stage("extract", 5)
    before_clauses = parse_documents(before)
    after_clauses = parse_documents(after)
    if not before_clauses or not after_clauses:
        raise RuntimeError("Не удалось извлечь текстовые фрагменты в одном из комплектов")
    record(
        AgentTraceEntry(
            agent="document_tools",
            action="extract",
            status="completed",
            summary=f"Извлечено фрагментов: до — {len(before_clauses)}, после — {len(after_clauses)}.",
        )
    )
    stage("structure", 20)
    registry = extract_registry(before_clauses, after_clauses, settings)
    record(
        AgentTraceEntry(
            agent="function_extractor",
            action="inventory",
            status="completed",
            summary=(
                f"Извлечено функций ДО/ПОСЛЕ: {registry.coverage.before_functions}/"
                f"{registry.coverage.after_functions}. Рассмотрено фрагментов: "
                f"{registry.coverage.reviewed_fragments}/{registry.coverage.total_fragments}."
            ),
        )
    )
    stage("compare", 45)
    function_links, added_ids = match_registry(registry, settings)
    registry = reconcile_mappings(registry, function_links, added_ids)
    record(
        AgentTraceEntry(
            agent="function_matcher",
            action="match_inventory",
            status="completed",
            summary=f"Пакетное сопоставление: получено решений ДО — {len(function_links)}; "
            f"явно новых записей ПОСЛЕ — {len(added_ids)}.",
        )
    )
    comparison = analyze_with_openai(before_clauses, after_clauses, settings)
    comparison.function_links = function_links
    comparison.added_after_ids = added_ids
    comparison.before_function_count = registry.coverage.before_functions
    comparison.after_function_count = registry.coverage.after_functions
    record(
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

    stage("verify", 70)
    initial_source_issues = source_issues(comparison, before_clauses, after_clauses, registry)
    record(
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
    assessment = evaluate_comparison(comparison, before_clauses, after_clauses, settings, registry)
    record(
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
        and any(issue.category != "coverage" for issue in assessment.issues)
    ):
        candidate = revise_with_openai(
            before_clauses, after_clauses, comparison, assessment, settings, registry
        )
        revisions += 1
        record(
            AgentTraceEntry(
                agent="comparison_agent",
                action="revise",
                status="completed",
                summary=f"Выполнено целевое исправление по замечаниям контролёра: {revisions}.",
            )
        )
        candidate_assessment = evaluate_comparison(
            candidate, before_clauses, after_clauses, settings, registry
        )
        record(
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
        source_errors = len(source_issues(comparison, before_clauses, after_clauses, registry))
        candidate_errors = len(source_issues(candidate, before_clauses, after_clauses, registry))
        if candidate_errors < source_errors or (
            candidate_errors == source_errors and candidate_assessment.score >= assessment.score
        ):
            comparison = candidate
            assessment = candidate_assessment
            record(
                AgentTraceEntry(
                    agent="orchestrator",
                    action="accept_revision",
                    status="completed",
                    summary="Исправленная версия принята с приоритетом проверяемости источников.",
                )
            )
        else:
            record(
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
    structural_risks, risk_warnings = build_structural_risks(comparison, before_clauses, after_clauses)
    warnings.extend(risk_warnings)
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
    record(
        AgentTraceEntry(
            agent="evidence_verifier",
            action="verify",
            status="completed",
            summary=(
                f"Проверены источники: принято {len(findings)} выводов и "
                f"{len(organization_changes)} изменений структуры; "
                f"потенциальных структурных рисков — {len(structural_risks)}."
            ),
        )
    )
    summary = make_summary(before_clauses, after_clauses, findings)
    registry = reconcile_mappings(registry, comparison.function_links, comparison.added_after_ids)
    summary.before_functions = registry.coverage.before_functions
    summary.after_functions = registry.coverage.after_functions
    summary.unchanged = sum(item.status == MappingStatus.UNCHANGED for item in registry.mappings)
    if registry.coverage.unresolved_fragments:
        warnings.append(
            f"Не закрыто извлечение фрагментов: {registry.coverage.unresolved_fragments}. "
            "Реестр функций неполон; проверьте список источников."
        )
    if registry.coverage.needs_review_mappings:
        warnings.append(
            f"Требуют проверки записи реестра: {registry.coverage.needs_review_mappings}."
        )
    warnings.append(
        "Количество функций ДО/ПОСЛЕ считается по реестру извлечённых обязанностей. "
        "Охват фрагментов не доказывает полноту извлечения или правильность сопоставления. "
        "Оценка контролёра не является измеренной точностью системы."
    )
    stage("report", 90)
    return PipelineResult(
        summary=summary,
        findings=findings,
        organization_changes=organization_changes,
        conclusion=build_conclusion(findings, organization_changes, warnings, structural_risks),
        warnings=warnings,
        agent_trace=trace,
        quality_score=assessment.score,
        function_registry=registry,
        structural_risks=structural_risks,
    )
