import asyncio

from app.schemas import Analysis


class AnalysisStore:
    """In-memory MVP store behind a replaceable interface."""

    def __init__(self) -> None:
        self._items: dict[str, Analysis] = {}
        self._lock = asyncio.Lock()

    async def put(self, analysis: Analysis) -> None:
        async with self._lock:
            self._items[analysis.id] = analysis

    async def get(self, analysis_id: str) -> Analysis | None:
        async with self._lock:
            return self._items.get(analysis_id)


store = AnalysisStore()

