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


def reverse_match(source_id="A0001-F01", targets=None, relation="unchanged"):
    return module.FunctionMatch(
        source_id=source_id,
        target_ids=["B0001-F01"] if targets is None else targets,
        relation=relation,
        reason="Найден кандидат в старой редакции",
    )


def test_reverse_candidate_recovers_omission_but_does_not_certify_it(monkeypatch):
    def match(sources, targets, settings):
        return module.MatchBatch(
            matches=[] if sources[0].side == DocumentSide.BEFORE else [reverse_match()]
        )

    monkeypatch.setattr(module, "match_batch_with_openai", match)
    data = inventory()
    links, added = module.match_registry(data, Settings())
    result = reconcile_mappings(data, links, added)
    assert added == []
    assert len(result.mappings) == 1
    assert result.mappings[0].after_ids == ["A0001-F01"]
    assert result.mappings[0].status == MappingStatus.NEEDS_REVIEW
    assert result.coverage.matched_before_functions == 0
    assert "Обратная сверка" in result.mappings[0].explanation


def test_reverse_candidate_contradicts_forward_loss():
    data = inventory()
    forward = [link(status="lost", after_ids=[])]
    merged = module.merge_reverse_candidates(data, forward, [reverse_match()])
    assert forward[0].status == "lost"  # Do not mutate prior stage's snapshot.
    assert merged[0].status == "needs_review"
    assert merged[0].after_ids == ["A0001-F01"]
    assert "Противоречие" in merged[0].explanation


@pytest.mark.parametrize("relation", ["unchanged", "changed", "moved", "needs_review"])
def test_reverse_split_keeps_original_link_and_requires_review(relation):
    data = inventory()
    data.functions.append(data.functions[1].model_copy(update={"id": "A0002-F01"}))
    merged = module.merge_reverse_candidates(
        data, [link()], [reverse_match("A0002-F01", relation=relation)]
    )
    assert len(merged) == 1
    assert merged[0].after_ids == ["A0001-F01", "A0002-F01"]
    assert merged[0].status == "needs_review"


def test_reverse_merge_keeps_both_before_functions_without_claiming_equivalence():
    data = inventory()
    data.functions.append(data.functions[0].model_copy(update={"id": "B0002-F01"}))
    merged = module.merge_reverse_candidates(
        data, [], [reverse_match(targets=["B0001-F01", "B0002-F01", "B0002-F01"])]
    )
    assert [row.before_id for row in merged] == ["B0001-F01", "B0002-F01"]
    assert all(row.after_ids == ["A0001-F01"] for row in merged)
    assert all(row.status == "needs_review" for row in merged)


@pytest.mark.parametrize(
    "reverse",
    [
        [reverse_match(source_id="unknown")],
        [reverse_match(targets=["unknown"])],
        [reverse_match(targets=["B0001-F01", "unknown"])],
        [reverse_match(targets=[])],
        [reverse_match(relation="absent")],
        [reverse_match(), reverse_match()],
    ],
)
def test_invalid_reverse_candidates_cannot_create_links(reverse):
    assert module.merge_reverse_candidates(inventory(), [], reverse) == []


def test_reverse_candidate_does_not_mask_duplicate_forward_decisions():
    links = [link(status="lost", after_ids=[]), link(status="lost", after_ids=[])]
    merged = module.merge_reverse_candidates(inventory(), links, [reverse_match()])
    result = reconcile_mappings(inventory(), merged, [])
    assert all(row.status == MappingStatus.NEEDS_REVIEW for row in result.mappings)
    assert all(not row.after_ids for row in merged)


def test_reverse_duplicate_edge_does_not_downgrade_valid_renumbering():
    merged = module.merge_reverse_candidates(inventory(), [link()], [reverse_match()])
    assert merged == [link()]


def test_reverse_candidates_still_obey_incomplete_source_guards():
    data = inventory()
    data.source_reviews[1].status = "needs_review"
    merged = module.merge_reverse_candidates(data, [], [reverse_match()])
    result = reconcile_mappings(data, merged, [])
    assert result.mappings[0].status == MappingStatus.NEEDS_REVIEW
    assert "Извлечение неполно" in result.mappings[0].explanation


def test_reverse_matching_respects_shared_batch_budget(monkeypatch):
    calls = []

    def match(sources, targets, settings):
        calls.append(sources)
        return module.MatchBatch(matches=[])

    monkeypatch.setattr(module, "match_batch_with_openai", match)
    links, added = module.match_registry(inventory(), Settings(registry_max_batches=1))
    assert len(calls) == 1
    assert links == added == []
