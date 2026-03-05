from __future__ import annotations

from app.config.settings import BackendSettings


class ConfigService:
    def __init__(self, settings: BackendSettings) -> None:
        self._settings = settings

    def deployment_profile(self) -> dict[str, str | int]:
        if self._settings.deployment_target == "windows":
            return {
                "platform": "windows",
                "reverse_proxy": "iis",
                "process_manager": "windows_service",
                "host": self._settings.service_host,
                "port": self._settings.service_port,
            }
        return {
            "platform": "linux",
            "reverse_proxy": "nginx",
            "process_manager": "systemd",
            "host": self._settings.service_host,
            "port": self._settings.service_port,
        }
