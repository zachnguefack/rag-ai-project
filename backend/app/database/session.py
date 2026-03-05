from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from app.config.settings import BackendSettings
from app.database.base import DatabaseInfo


class DatabaseSessionManager:
    """
    Session manager abstraction.

    The current repository implementation uses in-memory stores for local runs, while this
    manager carries SQL Server connection information required by enterprise deployments.
    """

    def __init__(self, settings: BackendSettings) -> None:
        self._settings = settings
        self._database_info = DatabaseInfo(url=settings.database_url)

    @property
    def database_info(self) -> DatabaseInfo:
        return self._database_info

    @contextmanager
    def session(self) -> Iterator[DatabaseInfo]:
        # Placeholder for SQLAlchemy SessionLocal when persistence is fully wired.
        yield self._database_info
