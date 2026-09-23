from app.analyzer import EvidenceDraft
from app.documents import Clause
from app.pipeline import evidence_index, normalize_clause, verify_evidence


def test_verifier_accepts_exact_source_quote() -> None:
    clauses = [
        Clause(
            document="Положение.docx",
            clause="3.4",
            text="Департамент осуществляет непрерывный мониторинг системы контроля.",
        )
    ]
    draft = EvidenceDraft(
        document="Положение.docx",
        clause="3.4",
        quote="осуществляет непрерывный мониторинг",
    )

    result = verify_evidence(draft, evidence_index(clauses))

    assert result is not None
    assert result.clause == "3.4"


def test_verifier_replaces_model_quote_with_exact_source() -> None:
    clauses = [Clause(document="Положение.docx", clause="3.4", text="Исходный текст пункта")]
    draft = EvidenceDraft(
        document="Положение.docx",
        clause="3.4",
        quote="Несуществующая функция подразделения",
    )

    result = verify_evidence(draft, evidence_index(clauses))

    assert result is not None
    assert result.quote == "Исходный текст пункта"


def test_clause_normalization_accepts_human_reference() -> None:
    assert normalize_clause("п. 3.4.") == "3.4"
