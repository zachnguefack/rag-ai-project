from __future__ import annotations

from app.database.session import DatabaseSessionManager


class UnitOfWork:
    """Transaction boundary abstraction for service-layer orchestration."""

    def __init__(self, session_manager: DatabaseSessionManager) -> None:
        self._session_manager = session_manager
        self._active = False

    def __enter__(self) -> UnitOfWork:
        self._active = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._active = False

    def commit(self) -> None:
        if not self._active:
            raise RuntimeError("Cannot commit outside active unit-of-work scope.")

    def rollback(self) -> None:
        if not self._active:
            raise RuntimeError("Cannot rollback outside active unit-of-work scope.")
