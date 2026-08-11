"""Immediate local notifications and asynchronous email dispatch."""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import threading
from pathlib import Path

from config import AppConfig
from email_notifier import EmailNotifier


def _apple_script_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


class MacOSNotifier:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def show(self, title: str, message: str) -> None:
        if platform.system() != "Darwin":
            self.logger.warning("macOS notification skipped: current OS is not macOS")
            return
        script = (
            f'display notification "{_apple_script_string(message)}" '
            f'with title "{_apple_script_string(title)}"'
        )
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.logger.info("macOS notification sent")

    def play_sound(self) -> None:
        if platform.system() != "Darwin":
            self.logger.warning("Sound notification skipped: current OS is not macOS")
            return
        sound = Path("/System/Library/Sounds/Glass.aiff")
        subprocess.Popen(
            ["afplay", str(sound)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.logger.info("Sound notification started")


class NotificationDispatcher:
    def __init__(
        self,
        config: AppConfig,
        smtp_password: str,
        logger: logging.Logger,
    ) -> None:
        self.config = config
        self.smtp_password = smtp_password or os.environ.get(
            "RESERVATION_MONITOR_SMTP_PASSWORD", ""
        )
        self.logger = logger
        self.local = MacOSNotifier(logger)
        self._email_threads: list[threading.Thread] = []

    def notify(self, reservation_url: str) -> None:
        # Local channels execute first; every channel is isolated from the others.
        if self.config.macos_notification_enabled:
            try:
                self.local.show(
                    "취소표 발생",
                    "네이버 예약 페이지에서 예약 가능 상태가 확인되었습니다. 지금 바로 확인하세요.",
                )
            except Exception:
                self.logger.exception("macOS notification failed")

        if self.config.sound_enabled:
            try:
                self.local.play_sound()
            except Exception:
                self.logger.exception("Sound notification failed")

        if self.config.email_enabled:
            thread = threading.Thread(
                target=self._send_email,
                args=(reservation_url,),
                name="reservation-email",
                daemon=True,
            )
            self._email_threads = [item for item in self._email_threads if item.is_alive()]
            self._email_threads.append(thread)
            thread.start()

    def _send_email(self, reservation_url: str) -> None:
        if not self.smtp_password:
            self.logger.error(
                "Email notification failed: SMTP password is empty. "
                "Enter an app password or set RESERVATION_MONITOR_SMTP_PASSWORD."
            )
            return
        try:
            notifier = EmailNotifier(
                host=self.config.smtp_host,
                port=self.config.smtp_port,
                username=self.config.smtp_username,
                password=self.smtp_password,
                sender=self.config.smtp_sender,
                recipient=self.config.email_recipient,
                use_tls=self.config.smtp_use_tls,
            )
            notifier.send_availability(reservation_url)
            self.logger.info("Email notification sent: %s", self.config.email_recipient)
        except Exception:
            self.logger.exception("Email notification failed")

    def close(self) -> None:
        # Email threads are daemon threads and intentionally do not block monitor shutdown.
        self._email_threads = [item for item in self._email_threads if item.is_alive()]
