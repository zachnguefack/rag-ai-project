from __future__ import annotations

import logging
import os

from app.config.settings import BackendSettings
from app.database.repositories.user_repo import UserRepository
from app.security.password import hash_password
from app.security.policies import RoleName
from app.services.rbac_service import RBACService

logger = logging.getLogger(__name__)

_DEFAULT_DEV_USERS: tuple[dict[str, object], ...] = (
    {
        "username": "admin",
        "email": "admin@local.dev",
        "password": "Admin123!",
        "roles": [RoleName.SUPER_ADMINISTRATOR],
        "label": "Super Administrator",
    },
    {
        "username": "sysadmin",
        "email": "sysadmin@local.dev",
        "password": "Admin123!",
        "roles": [RoleName.SYSTEM_ADMINISTRATOR],
        "label": "System Administrator",
    },
    {
        "username": "docadmin",
        "email": "docadmin@local.dev",
        "password": "Admin123!",
        "roles": [RoleName.DOCUMENT_ADMINISTRATOR],
        "label": "Document Administrator",
    },
    {
        "username": "poweruser",
        "email": "poweruser@local.dev",
        "password": "Admin123!",
        "roles": [RoleName.POWER_USER],
        "label": "Power User",
    },
    {
        "username": "user",
        "email": "user@local.dev",
        "password": "User123!",
        "roles": [RoleName.STANDARD_USER],
        "label": "Standard User",
    },
    {
        "username": "compliance",
        "email": "compliance@local.dev",
        "password": "Compliance123!",
        "roles": [RoleName.COMPLIANCE_OFFICER],
        "label": "Compliance Officer",
    },
)


def _bootstrap_enabled(settings: BackendSettings) -> bool:
    app_env = (os.getenv("APP_ENV", settings.app_env) or "").strip().lower()
    explicit_flag = (os.getenv("RAG_DEV_BOOTSTRAP_USERS", "false") or "").strip().lower() == "true"
    return app_env == "development" or explicit_flag


def seed_dev_rbac_users(settings: BackendSettings, rbac_service: RBACService) -> None:
    if not _bootstrap_enabled(settings):
        logger.info("[BOOTSTRAP] Development RBAC user bootstrap skipped (environment is not development).")
        return

    user_repo = UserRepository()
    if user_repo.count() > 0:
        logger.info("[BOOTSTRAP] Development RBAC user bootstrap skipped (users already exist).")
        return

    logger.info("[BOOTSTRAP] Creating default RBAC development users")
    for account in _DEFAULT_DEV_USERS:
        created = user_repo.create(
            username=str(account["username"]),
            email=str(account["email"]),
            password_hash=hash_password(str(account["password"])),
            roles=[],
        )
        rbac_service.replace_user_roles(created.user_id, list(account["roles"]))
        logger.info("[BOOTSTRAP] %s created: %s", account["label"], account["username"])
