"""Playwright persistent browser lifecycle management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class BrowserDependencyError(RuntimeError):
    """Raised when Playwright or its Chromium runtime is unavailable."""


class BrowserManager:
    def __init__(
        self,
        profile_dir: str,
        headless: bool,
        timeout_seconds: float,
        logger: logging.Logger,
    ) -> None:
        self.profile_dir = Path(profile_dir).expanduser()
        self.headless = headless
        self.timeout_ms = int(timeout_seconds * 1000)
        self.logger = logger
        self._playwright: Any = None
        self.context: Any = None
        self.page: Any = None

    def start(self) -> Any:
        if self.context is not None:
            return self.page
        try:
            from playwright.sync_api import Error as PlaywrightError
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserDependencyError(
                "Playwright가 설치되지 않았습니다. pip install -r requirements.txt 후 "
                "playwright install chromium을 실행하세요."
            ) from exc

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = sync_playwright().start()
        try:
            self.context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.profile_dir),
                headless=self.headless,
                viewport={"width": 1280, "height": 900},
                locale="ko-KR",
            )
        except PlaywrightError as exc:
            self._playwright.stop()
            self._playwright = None
            raise BrowserDependencyError(
                "Chromium을 시작하지 못했습니다. playwright install chromium을 실행한 뒤 재시도하세요."
            ) from exc

        self.context.set_default_timeout(self.timeout_ms)
        self.context.set_default_navigation_timeout(self.timeout_ms)
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.logger.info("Browser started (persistent profile: %s)", self.profile_dir)
        return self.page

    def visit(self, url: str) -> Any:
        page = self.start()
        page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        self.logger.info("Page opened: %s", url)
        return page

    def refresh(self) -> Any:
        if self.page is None:
            raise RuntimeError("Browser has not been started")
        self.page.reload(wait_until="domcontentloaded", timeout=self.timeout_ms)
        return self.page

    def restart(self, url: str) -> Any:
        self.logger.warning("Restarting browser after repeated errors")
        self.close()
        return self.visit(url)

    def is_login_page(self) -> bool:
        if self.page is None:
            return False
        host = (urlparse(self.page.url).hostname or "").lower()
        if host == "nid.naver.com" or host.endswith(".nid.naver.com"):
            return True
        try:
            return self.page.locator('input[type="password"]').count() > 0
        except Exception:
            return False

    def close(self) -> None:
        context, playwright = self.context, self._playwright
        self.context = None
        self.page = None
        self._playwright = None
        if context is not None:
            try:
                context.close()
            except Exception:
                self.logger.exception("Error while closing browser context")
        if playwright is not None:
            try:
                playwright.stop()
            except Exception:
                self.logger.exception("Error while stopping Playwright")
        if context is not None:
            self.logger.info("Browser stopped")
