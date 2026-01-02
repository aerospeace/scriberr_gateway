from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class SecurityConfig:
    api_key: str


@dataclass
class ScriberrConfig:
    base_url: str
    api_key: str


@dataclass
class AppriseConfig:
    url: str
    tag: str | None = None


DEFAULT_STATUS_COMPLETE = (
    "completed",
    "complete",
    "done",
    "finished",
    "succeeded",
)
DEFAULT_STATUS_FAILED = ("failed", "error", "canceled")


@dataclass
class ProcessingConfig:
    poll_interval_seconds: int = 10
    poll_timeout_seconds: int = 900
    status_complete_values: tuple[str, ...] = DEFAULT_STATUS_COMPLETE
    status_failed_values: tuple[str, ...] = DEFAULT_STATUS_FAILED


@dataclass
class AppConfig:
    server: ServerConfig
    security: SecurityConfig
    scriberr: ScriberrConfig
    apprise: AppriseConfig
    processing: ProcessingConfig


class ConfigError(RuntimeError):
    pass


DEFAULT_CONFIG_PATH = Path("config.yaml")


def _ensure_section(data: dict[str, Any], key: str) -> dict[str, Any]:
    section = data.get(key)
    if not isinstance(section, dict):
        raise ConfigError(f"Missing or invalid '{key}' section in config file")
    return section


def _tuple(value: Iterable[str] | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if value is None:
        return default
    return tuple(str(item).lower() for item in value)


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(
            f"Config file not found at {config_path}. "
            "Amend environment variable SCRIBERR_GATEWAY_CONFIG or create config.yaml "
        )

    raw = yaml.safe_load(config_path.read_text()) or {}
    if not isinstance(raw, dict):
        raise ConfigError("Config file must contain a YAML mapping")

    server_data = raw.get("server", {})
    server = ServerConfig(
        host=str(server_data.get("host", "0.0.0.0")),
        port=int(server_data.get("port", 8000)),
    )

    security_data = _ensure_section(raw, "security")
    security = SecurityConfig(api_key=str(security_data.get("api_key", "")).strip())
    if not security.api_key:
        raise ConfigError("security.api_key is required")

    scriberr_data = _ensure_section(raw, "scriberr")
    scriberr = ScriberrConfig(
        base_url=str(scriberr_data.get("base_url", "")).strip().rstrip("/"),
        api_key=str(scriberr_data.get("api_key", "")).strip(),
    )
    if not scriberr.base_url or not scriberr.api_key:
        raise ConfigError("scriberr.base_url and scriberr.api_key are required")

    apprise_data = _ensure_section(raw, "apprise")
    apprise = AppriseConfig(
        url=str(apprise_data.get("url", "")).strip(),
        tag=str(apprise_data.get("tag", "")).strip() or None,
    )
    if not apprise.url:
        raise ConfigError("apprise.url is required")

    processing_data = raw.get("processing", {})
    processing = ProcessingConfig(
        poll_interval_seconds=int(processing_data.get("poll_interval_seconds", 10)),
        poll_timeout_seconds=int(processing_data.get("poll_timeout_seconds", 900)),
        status_complete_values=_tuple(
            processing_data.get("status_complete_values"),
            DEFAULT_STATUS_COMPLETE,
        ),
        status_failed_values=_tuple(
            processing_data.get("status_failed_values"),
            DEFAULT_STATUS_FAILED,
        ),
    )

    return AppConfig(
        server=server,
        security=security,
        scriberr=scriberr,
        apprise=apprise,
        processing=processing,
    )
