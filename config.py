"""Application settings and persistence.

Passwords are deliberately excluded from this module.  SMTP passwords are read
from the GUI for the current process or from an environment variable.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


APP_DIR = Path.home() / ".reservation_monitor"
DEFAULT_CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_PROFILE_DIR = APP_DIR / "browser_profile"
DEFAULT_LOG_PATH = APP_DIR / "reservation_monitor.log"


@dataclass(slots=True)
class AppConfig:
    reservation_url: str = (
        "https://booking.naver.com/booking/12/bizes/1693898/items/7874774"
        "?startDateTime=2026-08-15T00%3A00%3A00%2B09%3A00"
    )
    check_interval: float = 3.0
    page_timeout_seconds: float = 20.0
    settle_time_ms: int = 700
    macos_notification_enabled: bool = True
    sound_enabled: bool = True
    email_enabled: bool = False
    email_recipient: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_sender: str = ""
    smtp_use_tls: bool = True
    available_selector: str = ""
    sold_out_selector: str = ""
    headless: bool = False
    profile_dir: str = str(DEFAULT_PROFILE_DIR)

    def validate(self) -> list[str]:
        errors: list[str] = []
        parsed = urlparse(self.reservation_url.strip())
        host = (parsed.hostname or "").lower()
        is_naver = host == "naver.me" or host.endswith(".naver.com") or host == "naver.com"
        if parsed.scheme not in {"http", "https"} or not host:
            errors.append("올바른 예약 페이지 URL을 입력하세요.")
        elif not is_naver:
            errors.append("네이버(naver.com 또는 naver.me) 예약 URL만 사용할 수 있습니다.")
        if not 2.0 <= self.check_interval <= 3600.0:
            errors.append("확인 주기는 서비스 부하를 고려해 2초 이상으로 설정하세요.")
        if not 5.0 <= self.page_timeout_seconds <= 120.0:
            errors.append("페이지 제한 시간은 5~120초로 설정하세요.")
        if not 0 <= self.settle_time_ms <= 10_000:
            errors.append("페이지 안정화 시간은 0~10000ms로 설정하세요.")
        if self.email_enabled:
            if not self.email_recipient.strip():
                errors.append("이메일 알림을 사용하려면 수신 주소를 입력하세요.")
            if not self.smtp_host.strip() or not self.smtp_username.strip():
                errors.append("이메일 알림을 사용하려면 SMTP 서버와 사용자 이름을 입력하세요.")
            if not 1 <= self.smtp_port <= 65535:
                errors.append("SMTP 포트가 올바르지 않습니다.")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AppConfig":
        allowed = {item.name for item in fields(cls)}
        values = {key: value for key, value in raw.items() if key in allowed}
        config = cls(**values)
        # JSON can be edited manually. Normalize numeric values here so malformed
        # preferences do not surface later as comparison TypeErrors in the GUI.
        config.check_interval = float(config.check_interval)
        config.page_timeout_seconds = float(config.page_timeout_seconds)
        config.settle_time_ms = int(config.settle_time_ms)
        config.smtp_port = int(config.smtp_port)
        return config


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("설정 파일의 최상위 값은 객체여야 합니다.")
        return AppConfig.from_dict(raw)
    except FileNotFoundError:
        return AppConfig()
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        # A bad local preference file must not prevent the GUI from opening.
        return AppConfig()


def save_config(config: AppConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)
