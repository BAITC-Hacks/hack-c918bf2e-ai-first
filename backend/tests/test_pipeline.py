from app.analyzer import EvidenceDraft
from app.documents import Clause
from app.pipeline import evidence_index, verify_evidence


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


def test_verifier_rejects_hallucinated_quote() -> None:
    clauses = [Clause(document="Положение.docx", clause="3.4", text="Исходный текст пункта")]
    draft = EvidenceDraft(
        document="Положение.docx",
        clause="3.4",
        quote="Несуществующая функция подразделения",
    )

    assert verify_evidence(draft, evidence_index(clauses)) is None
