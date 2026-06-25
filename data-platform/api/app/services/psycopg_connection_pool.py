from __future__ import annotations

from contextlib import contextmanager
from queue import Empty, Full, LifoQueue
from threading import Lock
from typing import Any, Iterator

import psycopg

from ..core.config import settings

_POOL_MIN_SIZE = 3
_POOL_MAX_SIZE = 30
_POOL_WAIT_TIMEOUT_SECONDS = 30.0


class RecommendationConnectionPool:
    def __init__(
        self,
        *,
        dsn: str,
        min_size: int,
        max_size: int,
        wait_timeout: float,
    ) -> None:
        if max_size < min_size:
            max_size = min_size
        self._dsn = dsn
        self._min_size = max(1, min_size)
        self._max_size = max(1, max_size)
        self._wait_timeout = max(1.0, wait_timeout)
        self._pool: LifoQueue[psycopg.Connection[Any]] = LifoQueue(
            maxsize=self._max_size
        )
        self._lock = Lock()
        self._created_count = 0
        self._closed = False

        for _ in range(self._min_size):
            self._pool.put(self._create_connection())
            self._created_count += 1

    def _create_connection(self) -> psycopg.Connection[Any]:
        conn = psycopg.connect(self._dsn)
        conn.autocommit = False
        return conn

    def _decrease_created_count(self) -> None:
        with self._lock:
            self._created_count = max(0, self._created_count - 1)

    def _acquire(self) -> psycopg.Connection[Any]:
        if self._closed:
            raise RuntimeError("Recommendation DB connection pool is closed.")

        try:
            conn = self._pool.get_nowait()
        except Empty:
            with self._lock:
                if self._created_count < self._max_size:
                    conn = self._create_connection()
                    self._created_count += 1
                    return conn
            conn = self._pool.get(timeout=self._wait_timeout)

        if conn.closed:
            self._decrease_created_count()
            with self._lock:
                if self._created_count < self._max_size:
                    conn = self._create_connection()
                    self._created_count += 1
                    return conn
            conn = self._pool.get(timeout=self._wait_timeout)

        return conn

    def _release(self, conn: psycopg.Connection[Any]) -> None:
        if conn.closed:
            self._decrease_created_count()
            return

        try:
            conn.rollback()
        except Exception:
            conn.close()
            self._decrease_created_count()
            return

        if self._closed:
            conn.close()
            self._decrease_created_count()
            return

        try:
            self._pool.put_nowait(conn)
        except Full:
            conn.close()
            self._decrease_created_count()

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[Any]]:
        conn = self._acquire()
        try:
            yield conn
        finally:
            self._release(conn)

    def close(self) -> None:
        self._closed = True
        while True:
            try:
                conn = self._pool.get_nowait()
            except Empty:
                break
            conn.close()
        with self._lock:
            self._created_count = 0


_connection_pool: RecommendationConnectionPool | None = None
_pool_lock = Lock()


def _database_dsn() -> str:
    return settings.database_url.replace("postgresql+asyncpg://", "postgresql://")


def get_recommendation_connection_pool() -> RecommendationConnectionPool:
    global _connection_pool
    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                _connection_pool = RecommendationConnectionPool(
                    dsn=_database_dsn(),
                    min_size=_POOL_MIN_SIZE,
                    max_size=_POOL_MAX_SIZE,
                    wait_timeout=_POOL_WAIT_TIMEOUT_SECONDS,
                )
    return _connection_pool


def close_recommendation_connection_pool() -> None:
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.close()
        _connection_pool = None
