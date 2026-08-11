"""Background monitoring loop, independent from the GUI."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from browser import BrowserManager
from config import AppConfig
from notification import NotificationDispatcher
from reservation_checker import (
    AvailabilityTransitionTracker,
    ReservationChecker,
    ReservationState,
)


@dataclass(slots=True)
class MonitorEvent:
    kind: str
    state: ReservationState | None = None
    checked_at: datetime | None = None
    message: str = ""
    evidence: tuple[str, ...] = ()


EventCallback = Callable[[MonitorEvent], None]


class MonitorService:
    def __init__(
        self,
        config: AppConfig,
        smtp_password: str,
        logger: logging.Logger,
        callback: EventCallback,
    ) -> None:
        self.config = config
        self.smtp_password = smtp_password
        self.logger = logger
        self.callback = callback
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="reservation-monitor",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def join(self, timeout: float | None = None) -> None:
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    def _run(self) -> None:
        browser = BrowserManager(
            profile_dir=self.config.profile_dir,
            headless=self.config.headless,
            timeout_seconds=self.config.page_timeout_seconds,
            logger=self.logger,
        )
        checker = ReservationChecker(
            available_selector=self.config.available_selector,
            sold_out_selector=self.config.sold_out_selector,
        )
        tracker = AvailabilityTransitionTracker()
        dispatcher = NotificationDispatcher(
            config=self.config,
            smtp_password=self.smtp_password,
            logger=self.logger,
        )
        consecutive_errors = 0
        first_navigation = True
        self.logger.info("Monitoring started")
        self.callback(MonitorEvent(kind="started", message="모니터링 중"))

        try:
            while not self._stop_event.is_set():
                cycle_started = datetime.now()
                try:
                    if first_navigation:
                        page = browser.visit(self.config.reservation_url)
                        first_navigation = False
                    else:
                        page = browser.refresh()
                    if self.config.settle_time_ms:
                        page.wait_for_timeout(self.config.settle_time_ms)
                    if browser.is_login_page():
                        self.logger.info("Login required; waiting for the user in the browser")
                        self.callback(
                            MonitorEvent(
                                kind="login",
                                state=ReservationState.UNKNOWN,
                                checked_at=datetime.now(),
                                message="브라우저에서 직접 로그인해 주세요. 로그인 완료까지 새로고침하지 않습니다.",
                            )
                        )
                        while not self._stop_event.is_set() and browser.is_login_page():
                            self._stop_event.wait(1.0)
                        first_navigation = True
                        consecutive_errors = 0
                        continue
                    result = checker.check(page)
                    consecutive_errors = 0
                    detected = tracker.observe(result.state)
                    checked_at = datetime.now()
                    evidence_text = "; ".join(result.evidence[:3])
                    self.logger.info(
                        "Current state: %s%s",
                        result.state.value,
                        f" ({evidence_text})" if evidence_text else "",
                    )
                    self.callback(
                        MonitorEvent(
                            kind="state",
                            state=result.state,
                            checked_at=checked_at,
                            message="취소표 감지" if detected else "",
                            evidence=tuple(result.evidence),
                        )
                    )
                    if detected:
                        self.logger.warning("Reservation availability detected")
                        dispatcher.notify(self.config.reservation_url)
                except Exception as exc:
                    consecutive_errors += 1
                    self.logger.exception(
                        "Monitoring cycle failed (%d/3)", consecutive_errors
                    )
                    self.callback(
                        MonitorEvent(
                            kind="error",
                            state=ReservationState.UNKNOWN,
                            checked_at=datetime.now(),
                            message=str(exc),
                        )
                    )
                    if consecutive_errors >= 3 and not self._stop_event.is_set():
                        try:
                            browser.restart(self.config.reservation_url)
                            first_navigation = False
                            consecutive_errors = 0
                            self.logger.info("Browser restart successful")
                        except Exception:
                            first_navigation = True
                            self.logger.exception("Browser restart failed; will retry")

                elapsed = (datetime.now() - cycle_started).total_seconds()
                remaining = max(0.0, self.config.check_interval - elapsed)
                self._stop_event.wait(remaining)
        finally:
            browser.close()
            dispatcher.close()
            self.logger.info("Monitoring stopped")
            self.callback(MonitorEvent(kind="stopped", message="중지됨"))
