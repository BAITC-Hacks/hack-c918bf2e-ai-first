import pytest

from app import registry as module
from app.config import Settings
from app.documents import Clause
from app.registry import (
    ExtractionBatch,
    FragmentDecision,
    FunctionDraft,
    FunctionLinkDraft,
    extract_registry,
    reconcile_mappings,
    update_coverage,
    validate_batch,
)
from app.schemas import DocumentSide, FunctionRegistry, MappingStatus


def decision(source_id="B0001", quote="Контролирует риски", status="functions"):
    return FragmentDecision(
        source_id=source_id,
        status=status,
        reason="Тест",
        functions=[FunctionDraft(action="Контроль рисков", owner=None, quote=quote)],
    )


def inventory() -> FunctionRegistry:
    result = FunctionRegistry()
    for side, key, number in (
        (DocumentSide.BEFORE, "B0001", "1.1"),
        (DocumentSide.AFTER, "A0001", "9.9"),
    ):
        functions, reviews = validate_batch(
            {key: Clause(f"{side}.docx", number, "Контролирует риски")},
            side,
            ExtractionBatch(decisions=[decision(key)]),
        )
        result.functions.extend(functions)
        result.source_reviews.extend(reviews)
    update_coverage(result)
    return result


def link(status="unchanged", after_ids=None) -> FunctionLinkDraft:
    return FunctionLinkDraft(
        before_id="B0001-F01",
        after_ids=after_ids if after_ids is not None else ["A0001-F01"],
        status=status,
        explanation="Сопоставлено по смыслу",
    )


def test_missing_and_hallucinated_sources_are_visible():
    sources = {
        "B0001": Clause("x.docx", "1", "Контролирует риски"),
        "B0002": Clause("x.docx", "2", "Готовит отчёты"),
    }
    functions, reviews = validate_batch(
        sources, DocumentSide.BEFORE, ExtractionBatch(decisions=[decision("made-up")])
    )
    assert functions == []
    assert len(reviews) == 2
    assert all(item.status == "needs_review" for item in reviews)


def test_bad_quote_does_not_count_as_completed_extraction():
    functions, reviews = validate_batch(
        {"B0001": Clause("x.docx", "1", "Контролирует риски")},
        DocumentSide.BEFORE,
        ExtractionBatch(decisions=[decision(quote="Несуществующая обязанность")]),
    )
    assert not functions
    assert reviews[0].status == "needs_review"


def test_duplicate_decisions_are_ambiguous():
    functions, reviews = validate_batch(
        {"B0001": Clause("x.docx", "1", "Контролирует риски")},
        DocumentSide.BEFORE,
        ExtractionBatch(decisions=[decision(), decision()]),
    )
    assert not functions
    assert reviews[0].status == "needs_review"


def test_nonfunctional_decision_is_recorded_but_not_a_function():
    draft = FragmentDecision(
        source_id="B0001", status="non_functional", functions=[], reason="Заголовок"
    )
    functions, reviews = validate_batch(
        {"B0001": Clause("x.docx", "1", "Общие положения")},
        DocumentSide.BEFORE,
        ExtractionBatch(decisions=[draft]),
    )
    assert functions == []
    assert reviews[0].status == "non_functional"


def test_multiple_atomic_functions_in_one_clause():
    draft = decision()
    draft.functions.append(FunctionDraft(action="Отчёт", owner=None, quote="Готовит отчёты"))
    functions, reviews = validate_batch(
        {"B0001": Clause("x.docx", "1", "Контролирует риски. Готовит отчёты.")},
        DocumentSide.BEFORE,
        ExtractionBatch(decisions=[draft]),
    )
    assert [item.id for item in functions] == ["B0001-F01", "B0001-F02"]
    assert reviews[0].status == "functions"


def test_omitted_mapping_is_needs_review_not_loss_or_addition():
    result = reconcile_mappings(inventory(), [], [])
    assert len(result.mappings) == 2
    assert all(row.status == MappingStatus.NEEDS_REVIEW for row in result.mappings)
    assert result.coverage.needs_review_mappings == 2


def test_renumbered_sources_can_be_preserved():
    result = reconcile_mappings(inventory(), [link()], [])
    assert result.mappings[0].status == MappingStatus.UNCHANGED
    assert result.coverage.matched_before_functions == 1
    assert result.coverage.needs_review_mappings == 0


@pytest.mark.parametrize(
    "drafts",
    [[link(after_ids=["unknown"])], [link(), link()], [link(status="lost")], [link(after_ids=[])]],
)
def test_invalid_mapping_never_closes_coverage(drafts):
    result = reconcile_mappings(inventory(), drafts, [])
    assert result.mappings[0].status == MappingStatus.NEEDS_REVIEW
    assert result.coverage.matched_before_functions == 0


def test_incomplete_extraction_blocks_loss_and_addition():
    data = inventory()
    data.source_reviews[1].status = "needs_review"
    result = reconcile_mappings(data, [link(status="lost", after_ids=[])], [])
    assert result.mappings[0].status == MappingStatus.NEEDS_REVIEW
    data = inventory()
    data.source_reviews[0].status = "needs_review"
    result = reconcile_mappings(data, [], ["A0001-F01"])
    assert result.mappings[-1].status == MappingStatus.NEEDS_REVIEW


def test_new_and_matched_is_a_contradiction():
    result = reconcile_mappings(inventory(), [link()], ["A0001-F01"])
    assert result.mappings[0].status == MappingStatus.NEEDS_REVIEW


def test_loss_and_addition_require_explicit_decisions():
    result = reconcile_mappings(inventory(), [link(status="lost", after_ids=[])], ["A0001-F01"])
    assert [row.status for row in result.mappings] == [MappingStatus.LOST, MappingStatus.ADDED]


def test_failed_batch_and_budget_limit_preserve_all_fragments(monkeypatch):
    calls = []

    def fail(sources, settings):
        calls.append(sources)
        raise TimeoutError("Test")

    monkeypatch.setattr(module, "extract_batch_with_openai", fail)
    result = extract_registry(
        [Clause("before", "1", "Контроль"), Clause("before", "2", "Отчёт")],
        [Clause("after", "1", "Контроль")],
        Settings(registry_batch_size=1, registry_max_batches=1),
    )
    assert len(calls) == 1
    assert result.coverage.total_fragments == 3
    assert result.coverage.unresolved_fragments == 3
    assert not result.functions


def test_matcher_keeps_all_sources_and_opposite_inventory(monkeypatch):
    data = inventory()
    original = data.functions[0]
    data.functions.extend(
        original.model_copy(update={"id": f"extra-{index}"}) for index in range(4)
    )
    jobs = []

    def match(sources, targets, settings):
        jobs.append(([item.id for item in sources], [item.id for item in targets]))
        return module.MatchBatch(
            matches=[
                module.FunctionMatch(
                    source_id=source.id,
                    target_ids=["A0001-F01"],
                    relation="unchanged",
                    reason="Тест",
                )
                for source in sources
            ]
        )

    monkeypatch.setattr(module, "match_batch_with_openai", match)
    links, added = module.match_registry(data, Settings(registry_match_batch_size=2))
    assert len(links) == 5
    assert len(jobs) == 3
    assert all(len(sources) <= 2 and targets == ["A0001-F01"] for sources, targets in jobs)
    assert added == []


def test_matcher_failure_does_not_manufacture_loss(monkeypatch):
    def fail(*args):
        raise TimeoutError("Test")

    monkeypatch.setattr(module, "match_batch_with_openai", fail)
    data = inventory()
    links, added = module.match_registry(data, Settings())
    result = reconcile_mappings(data, links, added)
    assert all(item.status == MappingStatus.NEEDS_REVIEW for item in result.mappings)
