from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DatabaseInfo:
    """Lightweight database metadata used by repositories and health checks."""

    url: str

    @property
    def is_sql_server(self) -> bool:
        return self.url.startswith("mssql+") or "sql server" in self.url.lower()
