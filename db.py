"""PostgreSQL history storage for Locatify.

Optional: when DATABASE_URL is not set (for example in local development) the scraper still works and
history is simply unavailable. Database errors are logged and never interrupt a running scrape.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any

import asyncpg

log = logging.getLogger("maps-scraper")

SCHEMA = """
CREATE TABLE IF NOT EXISTS searches (
    id           BIGSERIAL PRIMARY KEY,
    query        TEXT        NOT NULL,
    max_results  INTEGER     NOT NULL,
    delay        REAL        NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'running',
    result_count INTEGER     NOT NULL DEFAULT 0,
    file_id      TEXT,
    error        TEXT,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS searches_started_idx ON searches (started_at DESC);

CREATE TABLE IF NOT EXISTS places (
    id           BIGSERIAL PRIMARY KEY,
    search_id    BIGINT  NOT NULL REFERENCES searches (id) ON DELETE CASCADE,
    position     INTEGER NOT NULL,
    name         TEXT    NOT NULL,
    address      TEXT    NOT NULL DEFAULT '',
    phone        TEXT    NOT NULL DEFAULT '',
    website      TEXT    NOT NULL DEFAULT '',
    rating       TEXT    NOT NULL DEFAULT '',
    review_count TEXT    NOT NULL DEFAULT '',
    category     TEXT    NOT NULL DEFAULT '',
    maps_url     TEXT    NOT NULL DEFAULT '',
    email        TEXT    NOT NULL DEFAULT '',
    place_id     TEXT    NOT NULL DEFAULT '',
    cid          TEXT    NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS places_search_idx ON places (search_id, position);
"""

PLACE_FIELDS = (
    "name",
    "address",
    "phone",
    "website",
    "rating",
    "review_count",
    "category",
    "maps_url",
    "email",
    "place_id",
    "cid",
)
RETRY_SECONDS = 10

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()
_last_failure = 0.0


def configured() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


async def get_pool() -> asyncpg.Pool | None:
    """Return the connection pool, creating it lazily (the database may start after the app)."""
    global _pool, _last_failure
    if _pool is not None:
        return _pool
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return None
    async with _pool_lock:
        if _pool is not None:
            return _pool
        if time.monotonic() - _last_failure < RETRY_SECONDS:
            return None
        try:
            pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5, command_timeout=20)
            async with pool.acquire() as conn:
                await conn.execute(SCHEMA)
                # Only one scrape runs at a time, so any "running" row left over is from a crashed process.
                await conn.execute(
                    "UPDATE searches SET status = 'interrupted', finished_at = now() WHERE status = 'running'"
                )
            _pool = pool
            log.info("History database connected")
        except Exception as exc:
            _last_failure = time.monotonic()
            log.error("History database unavailable: %s", exc)
            return None
    return _pool


async def close() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def start_search(query: str, max_results: int, delay: float) -> int | None:
    pool = await get_pool()
    if pool is None:
        return None
    try:
        return await pool.fetchval(
            "INSERT INTO searches (query, max_results, delay) VALUES ($1, $2, $3) RETURNING id",
            query,
            max_results,
            delay,
        )
    except Exception as exc:
        log.error("Could not record search: %s", exc)
        return None


async def add_place(search_id: int | None, position: int, place: dict[str, str]) -> None:
    if search_id is None or _pool is None:
        return
    try:
        await _pool.execute(
            f"INSERT INTO places (search_id, position, {', '.join(PLACE_FIELDS)})"
            f" VALUES ($1, $2, {', '.join(f'${i}' for i in range(3, 3 + len(PLACE_FIELDS)))})",
            search_id,
            position,
            *[(place.get(field) or "") for field in PLACE_FIELDS],
        )
    except Exception as exc:
        log.error("Could not record place %r: %s", place.get("name"), exc)


async def finish_search(
    search_id: int | None,
    status: str,
    count: int,
    file_id: str | None = None,
    error: str | None = None,
) -> None:
    if search_id is None or _pool is None:
        return
    try:
        await _pool.execute(
            "UPDATE searches SET status = $2, result_count = $3, file_id = $4, error = $5, finished_at = now()"
            " WHERE id = $1",
            search_id,
            status,
            count,
            file_id,
            error,
        )
    except Exception as exc:
        log.error("Could not finish search %s: %s", search_id, exc)


def _search_dict(row: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": row["id"],
        "query": row["query"],
        "max_results": row["max_results"],
        "status": row["status"],
        "count": row["result_count"],
        "error": row["error"],
        "started_at": row["started_at"].isoformat(),
        "finished_at": row["finished_at"].isoformat() if row["finished_at"] else None,
    }


async def list_searches(limit: int, offset: int, text: str = "") -> dict[str, Any] | None:
    pool = await get_pool()
    if pool is None:
        return None
    pattern = f"%{text.strip()}%" if text.strip() else "%"
    total = await pool.fetchval("SELECT count(*) FROM searches WHERE query ILIKE $1", pattern)
    rows = await pool.fetch(
        "SELECT * FROM searches WHERE query ILIKE $1 ORDER BY started_at DESC, id DESC LIMIT $2 OFFSET $3",
        pattern,
        limit,
        offset,
    )
    return {"total": total, "items": [_search_dict(row) for row in rows]}


async def get_search(search_id: int) -> dict[str, Any] | None:
    """Return one search with its places, or None when it does not exist (or the database is down)."""
    pool = await get_pool()
    if pool is None:
        return None
    row = await pool.fetchrow("SELECT * FROM searches WHERE id = $1", search_id)
    if row is None:
        return None
    places = await pool.fetch(
        f"SELECT {', '.join(PLACE_FIELDS)} FROM places WHERE search_id = $1 ORDER BY position",
        search_id,
    )
    return {**_search_dict(row), "places": [dict(place) for place in places]}
