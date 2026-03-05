from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True, slots=True)
class UserContext:
    user_id: str
    role: str


class DocumentAccessControlService:
    """Build metadata filters that enforce document-level access prior to retrieval."""

    GLOBAL_ACCESS_ROLES = {"system_administrator", "super_administrator"}

    def __init__(self, policy_path: Path, data_dir: Path):
        self._policy_path = policy_path
        self._data_dir = data_dir.resolve()

    def _load_policy(self) -> Dict[str, Any]:
        if not self._policy_path.exists():
            return {"default_visibility": "private", "documents": {}}
        with self._policy_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _normalize_source(self, source: str) -> str:
        p = Path(source)
        if not p.is_absolute():
            p = self._data_dir / p
        return str(p.resolve())

    @staticmethod
    def _combine_filters(existing_filter: Optional[Dict[str, Any]], access_filter: Dict[str, Any]) -> Dict[str, Any]:
        if not existing_filter:
            return access_filter
        return {"$and": [existing_filter, access_filter]}

    def build_access_filter(
        self,
        user: UserContext,
        metadata_filter: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if user.role in self.GLOBAL_ACCESS_ROLES:
            return metadata_filter or {}

        policy = self._load_policy()
        default_visibility = str(policy.get("default_visibility", "private")).lower()
        doc_rules: Dict[str, Dict[str, Any]] = policy.get("documents", {}) or {}

        allowed_sources = []
        for source, rule in doc_rules.items():
            normalized_source = self._normalize_source(source)
            if self._is_allowed(user, rule):
                allowed_sources.append(normalized_source)

        if default_visibility == "public":
            # Public-by-default: filter only explicit denies via "denied_users" / "denied_roles".
            deny_conditions = {
                "$and": [
                    {"denied_users": {"$ne": user.user_id}},
                    {"denied_roles": {"$ne": user.role}},
                ]
            }
            if allowed_sources:
                return self._combine_filters(
                    metadata_filter,
                    {"$or": [{"source": {"$in": sorted(set(allowed_sources))}}, deny_conditions]},
                )
            return self._combine_filters(metadata_filter, deny_conditions)

        if not allowed_sources:
            # Always deny when no documents are accessible.
            return self._combine_filters(metadata_filter, {"source": "__no_access__"})

        return self._combine_filters(metadata_filter, {"source": {"$in": sorted(set(allowed_sources))}})

    @staticmethod
    def _is_allowed(user: UserContext, rule: Dict[str, Any]) -> bool:
        if not rule:
            return False

        if bool(rule.get("public", False)):
            return True

        owner_id = rule.get("owner_id")
        if owner_id and owner_id == user.user_id:
            return True

        allowed_users = set(rule.get("allowed_users", []) or [])
        if user.user_id in allowed_users:
            return True

        allowed_roles = set(rule.get("allowed_roles", []) or [])
        if user.role in allowed_roles:
            return True

        return False
