"""Local preflight checks that do not access the reservation page."""

from __future__ import annotations

import argparse
import logging
import platform
import sys


def run_checks(send_notification: bool = False) -> int:
    failures: list[str] = []

    print(f"[정보] OS: {platform.system()} {platform.release()}")
    print(f"[정보] Python: {platform.python_version()}")
    if sys.version_info < (3, 10):
        failures.append("Python 3.10 이상이 필요합니다.")

    try:
        import tkinter  # noqa: F401

        print("[정상] Tkinter GUI")
    except ImportError as exc:
        failures.append(f"Tkinter를 불러오지 못했습니다: {exc}")

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content("<title>Reservation Monitor Check</title><p>ok</p>")
            if page.title() != "Reservation Monitor Check":
                raise RuntimeError("브라우저 페이지 확인 결과가 올바르지 않습니다.")
            browser.close()
        print("[정상] Playwright Chromium")
    except Exception as exc:
        failures.append(f"Playwright Chromium을 실행하지 못했습니다: {exc}")

    if send_notification and platform.system() == "Darwin":
        try:
            from notification import MacOSNotifier

            notifier = MacOSNotifier(logging.getLogger("reservation_monitor.doctor"))
            notifier.show("Reservation Monitor", "macOS 알림 테스트에 성공했습니다.")
            notifier.play_sound()
            print("[정상] macOS 알림 및 사운드 요청")
        except Exception as exc:
            failures.append(f"macOS 알림 테스트에 실패했습니다: {exc}")

    if failures:
        for failure in failures:
            print(f"[실패] {failure}", file=sys.stderr)
        return 1

    print("[완료] 기본 실행 환경이 정상입니다.")
    if not send_notification and platform.system() == "Darwin":
        print("알림까지 시험하려면: .venv/bin/python doctor.py --notify")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Reservation Monitor 환경 점검")
    parser.add_argument(
        "--notify",
        action="store_true",
        help="macOS 알림과 사운드도 한 번 시험합니다.",
    )
    args = parser.parse_args()
    return run_checks(send_notification=args.notify)


if __name__ == "__main__":
    raise SystemExit(main())
