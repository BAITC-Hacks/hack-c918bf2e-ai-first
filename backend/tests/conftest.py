import pytest

from app import registry


@pytest.fixture
def stub_registry_model(monkeypatch):
    """Replace only the provider, retaining real inventory validation and coverage."""

    def extract(sources, settings):
        return registry.ExtractionBatch(
            decisions=[
                registry.FragmentDecision(
                    source_id=key,
                    status="functions",
                    reason="Тестовая обязанность",
                    functions=[
                        registry.FunctionDraft(action=clause.text, owner=None, quote=clause.text)
                    ],
                )
                for key, clause in sources.items()
            ]
        )

    monkeypatch.setattr(registry, "extract_batch_with_openai", extract)

    def match(sources, targets, settings):
        matches = []
        for source in sources:
            words = set(source.action.lower().split())
            target = next(
                (item for item in targets if words & set(item.action.lower().split())), None
            )
            relation = (
                "absent"
                if target is None
                else ("unchanged" if source.action == target.action else "changed")
            )
            matches.append(
                registry.FunctionMatch(
                    source_id=source.id,
                    target_ids=[target.id] if target else [],
                    relation=relation,
                    reason="Контрольная заглушка",
                )
            )
        return registry.MatchBatch(matches=matches)

    monkeypatch.setattr(registry, "match_batch_with_openai", match)
