from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    READ_DOCUMENT = "read:document"
    SEARCH_DOCUMENT = "search:document"
    INGEST_DOCUMENT = "ingest:document"
    UPDATE_DOCUMENT = "update:document"
    DELETE_DOCUMENT = "delete:document"
    READ_AUDIT_LOG = "read:audit-log"
    EXPORT_AUDIT_LOG = "export:audit-log"
    MANAGE_USERS = "manage:users"
    MANAGE_ROLES = "manage:roles"
    MANAGE_SYSTEM = "manage:system"


class RoleName(StrEnum):
    STANDARD_USER = "standard_user"
    POWER_USER = "power_user"
    DOCUMENT_ADMINISTRATOR = "document_administrator"
    COMPLIANCE_OFFICER = "compliance_officer"
    SYSTEM_ADMINISTRATOR = "system_administrator"
    SUPER_ADMINISTRATOR = "super_administrator"


ROLE_PERMISSION_MAP: dict[RoleName, frozenset[Permission]] = {
    RoleName.STANDARD_USER: frozenset({Permission.READ_DOCUMENT, Permission.SEARCH_DOCUMENT}),
    RoleName.POWER_USER: frozenset(
        {
            Permission.READ_DOCUMENT,
            Permission.SEARCH_DOCUMENT,
            Permission.INGEST_DOCUMENT,
            Permission.UPDATE_DOCUMENT,
        }
    ),
    RoleName.DOCUMENT_ADMINISTRATOR: frozenset(
        {
            Permission.READ_DOCUMENT,
            Permission.SEARCH_DOCUMENT,
            Permission.INGEST_DOCUMENT,
            Permission.UPDATE_DOCUMENT,
            Permission.DELETE_DOCUMENT,
        }
    ),
    RoleName.COMPLIANCE_OFFICER: frozenset(
        {
            Permission.READ_DOCUMENT,
            Permission.SEARCH_DOCUMENT,
            Permission.READ_AUDIT_LOG,
            Permission.EXPORT_AUDIT_LOG,
        }
    ),
    RoleName.SYSTEM_ADMINISTRATOR: frozenset(
        {
            Permission.READ_DOCUMENT,
            Permission.SEARCH_DOCUMENT,
            Permission.INGEST_DOCUMENT,
            Permission.UPDATE_DOCUMENT,
            Permission.DELETE_DOCUMENT,
            Permission.MANAGE_USERS,
            Permission.MANAGE_ROLES,
            Permission.MANAGE_SYSTEM,
            Permission.READ_AUDIT_LOG,
            Permission.EXPORT_AUDIT_LOG,
        }
    ),
    RoleName.SUPER_ADMINISTRATOR: frozenset(permission for permission in Permission),
}

DOCUMENT_GLOBAL_ACCESS_ROLES: frozenset[RoleName] = frozenset(
    {
        RoleName.DOCUMENT_ADMINISTRATOR,
        RoleName.COMPLIANCE_OFFICER,
        RoleName.SYSTEM_ADMINISTRATOR,
        RoleName.SUPER_ADMINISTRATOR,
    }
)
