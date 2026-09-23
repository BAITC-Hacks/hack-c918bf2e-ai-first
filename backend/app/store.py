"""Durable, validated analysis snapshots; no silent in-memory fallback in production."""

import asyncio
import re

import asyncpg

from app.schemas import Analysis, AnalysisError, AnalysisStatus, StepStatus

INTERRUPTED_MESSAGE = (
    "Анализ прерван при остановке сервиса. Сохранён последний этап. "
    "Загрузите исходные документы и запустите анализ заново; "
    "автоматический повтор платных запросов не выполнялся."
)


def mark_interrupted(analysis: Analysis) -> None:
    analysis.status = AnalysisStatus.FAILED
    analysis.current_step = "Запуск прерван"
    analysis.error = AnalysisError(code="ANALYSIS_INTERRUPTED", message=INTERRUPTED_MESSAGE)
    for step in analysis.steps:
        if step.status == StepStatus.PROCESSING:
            step.status = StepStatus.FAILED


class MemoryAnalysisStore:
    """Explicit test double. JSON snapshots mirror database isolation/serialization."""

    def __init__(self) -> None:
        self._items: dict[str, str] = {}

    async def start(self) -> int:
        recovered = 0
        for payload in list(self._items.values()):
            analysis = Analysis.model_validate_json(payload)
            if analysis.status in {AnalysisStatus.QUEUED, AnalysisStatus.PROCESSING}:
                mark_interrupted(analysis)
                await self.put(analysis)
                recovered += 1
        return recovered

    async def close(self) -> None:
        pass

    async def healthy(self) -> bool:
        return True

    async def put(self, analysis: Analysis) -> None:
        self._items[analysis.id] = analysis.model_dump_json()

    async def get(self, analysis_id: str) -> Analysis | None:
        payload = self._items.get(analysis_id)
        return Analysis.model_validate_json(payload) if payload is not None else None


class PostgresAnalysisStore:
    """One backend worker owns recovery. A session lock rejects a second worker.

    ``schema`` isolates integration tests from actual analyses. Production uses
    public. All payloads retain the public API shape.
    """

    def __init__(self, database_url: str, *, schema: str = "public") -> None:
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", schema):
            raise ValueError("Invalid database schema")
        self._dsn = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        self._schema = schema
        self._pool: asyncpg.Pool | None = None
        self._guard: asyncpg.Connection | None = None

    async def start(self) -> int:
        if not self._dsn:
            raise RuntimeError("DATABASE_URL is required; in-memory storage is test-only")
        if self._pool is not None or self._guard is not None:
            raise RuntimeError("Analysis store is already started")
        options = {"server_settings": {"search_path": self._schema}, "timeout": 10,
                   "command_timeout": 10}
        try:
            self._guard = await asyncpg.connect(self._dsn, **options)
            locked = await self._guard.fetchval(
                "SELECT pg_try_advisory_lock(hashtext(current_database()), hashtext($1))",
                f"ai_first_analysis_worker:{self._schema}",
            )
            if not locked:
                raise RuntimeError("Only one backend worker is supported; another worker is active")
            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5, **options)
            await self._pool.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    payload JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )
            """)
            # Recovery is atomic and must finish before serving requests.
            async with (
                self._pool.acquire(timeout=10) as connection,
                connection.transaction(),
            ):
                rows = await connection.fetch("""
                    SELECT payload FROM analyses
                    WHERE payload->>'status' IN ('queued', 'processing') FOR UPDATE
                """)
                for row in rows:
                    analysis = Analysis.model_validate_json(row["payload"])
                    mark_interrupted(analysis)
                    await connection.execute(
                        "UPDATE analyses SET payload=$2::jsonb, updated_at=now() WHERE id=$1",
                        analysis.id, analysis.model_dump_json(),
                    )
            return len(rows)
        except BaseException:
            await self.close()
            raise

    def _connection_pool(self) -> asyncpg.Pool:
        if self._pool is None or self._guard is None or self._guard.is_closed():
            raise ConnectionError("Analysis storage unavailable; restart the backend")
        return self._pool

    async def healthy(self) -> bool:
        pool = self._connection_pool()
        async with pool.acquire(timeout=5) as connection:
            return await connection.fetchval("SELECT 1") == 1

    async def put(self, analysis: Analysis) -> None:
        # Serialize before awaiting: callers cannot mutate an in-flight snapshot.
        payload = analysis.model_dump_json()
        pool = self._connection_pool()
        async with pool.acquire(timeout=10) as connection:
            await connection.execute("""
                INSERT INTO analyses (id, payload) VALUES ($1, $2::jsonb)
                ON CONFLICT (id) DO UPDATE SET payload=EXCLUDED.payload, updated_at=now()
            """, analysis.id, payload)

    async def get(self, analysis_id: str) -> Analysis | None:
        pool = self._connection_pool()
        async with pool.acquire(timeout=10) as connection:
            payload = await connection.fetchval("SELECT payload FROM analyses WHERE id=$1", analysis_id)
        return Analysis.model_validate_json(payload) if payload is not None else None

    async def close(self) -> None:
        pool, guard = self._pool, self._guard
        self._pool = None
        self._guard = None
        try:
            if pool is not None:
                await asyncio.wait_for(pool.close(), timeout=10)
        finally:
            if guard is not None:
                await guard.close(timeout=5)
