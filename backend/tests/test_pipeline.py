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


def test_verifier_rejects_hallucinated_quote() -> None:
    clauses = [Clause(document="Положение.docx", clause="3.4", text="Исходный текст пункта")]
    draft = EvidenceDraft(
        document="Положение.docx",
        clause="3.4",
        quote="Несуществующая функция подразделения",
    )

    result = verify_evidence(draft, evidence_index(clauses))

    assert result is None


def test_clause_normalization_accepts_human_reference() -> None:
    assert normalize_clause("п. 3.4.") == "3.4"


def test_verifier_rejects_wrong_document_even_with_unique_number() -> None:
    clauses = [Clause("real.docx", "3.4", "Исходный текст пункта")]
    draft = EvidenceDraft(document="fake.docx", clause="3.4", quote="Исходный текст")
    assert verify_evidence(draft, evidence_index(clauses)) is None


def test_verifier_rejects_ambiguous_source() -> None:
    clauses = [Clause("same.docx", "1.1", "Текст"), Clause("same.docx", "1.1", "Текст")]
    draft = EvidenceDraft(document="same.docx", clause="1.1", quote="Текст")
    assert verify_evidence(draft, evidence_index(clauses)) is None


def test_structural_reference_is_not_truncated_to_a_number() -> None:
    assert normalize_clause("3.4 [фрагмент 2]") == "3.4 [фрагмент 2]"
    assert normalize_clause("Лист 3.4!10") == "лист 3.4!10"


def test_verifier_preserves_exact_substring_far_from_start() -> None:
    clauses = [Clause("real.docx", "1.1", "Начало " * 300 + "Контроль\n качества процессов")]
    draft = EvidenceDraft(document="real.docx", clause="1.1", quote="контроль качества процессов")
    result = verify_evidence(draft, evidence_index(clauses))
    assert result is not None
    assert result.quote == "Контроль\n качества процессов"
