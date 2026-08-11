"""Conservative DOM-based reservation availability classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReservationState(str, Enum):
    AVAILABLE = "AVAILABLE"
    SOLD_OUT = "SOLD_OUT"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True)
class DetectionResult:
    state: ReservationState
    evidence: list[str] = field(default_factory=list)


# This script inspects semantics and element state rather than unstable generated classes.
# It intentionally requires strong positive evidence before returning AVAILABLE.
DOM_INSPECTION_SCRIPT = r"""
({availableSelector, soldOutSelector}) => {
  const visible = (el) => {
    const style = window.getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' &&
      Number(style.opacity || 1) > 0 && rect.width > 0 && rect.height > 0;
  };
  const textOf = (el) => (el.innerText || el.textContent || el.getAttribute('aria-label') || '')
    .replace(/\s+/g, ' ').trim();
  const disabled = (el) => Boolean(el.disabled) || el.getAttribute('aria-disabled') === 'true' ||
    /(^|\s)(disabled|is-disabled)(\s|$)/i.test(String(el.className || ''));
  const naverUnselectable = (el) =>
    /(^|\s)unselectable(\s|$)/i.test(String(el.className || ''));
  const actionable = (el) => ['A', 'BUTTON'].includes(el.tagName) ||
    ['button', 'link'].includes(el.getAttribute('role')) || el.tabIndex >= 0;
  const positive = /(^|\s)(예약하기|예약 가능|예매하기|신청하기|예약 신청)(\s|$)/;
  const exactPositive = /^(예약|예매|신청)$/;
  const positiveExclusion = /(예약 내역|예약내역|예약 안내|예약안내|예약 확인|예약확인|예약 변경|예약변경|예약 취소|예약취소)/;
  const negative = /(매진|예약\s*마감|예약\s*불가|판매\s*종료|신청\s*마감|잔여\s*(좌석|수량)\s*없음)/;
  const result = {
    customAvailable: [], customSoldOut: [], available: [], soldOut: [],
    naver: {present: false, selectedDate: null, timeSlots: []}
  };

  const custom = (selector, key) => {
    if (!selector) return;
    try {
      document.querySelectorAll(selector).forEach((el) => {
        if (visible(el)) result[key].push(textOf(el).slice(0, 160) || selector);
      });
    } catch (error) {
      result[key + 'Error'] = String(error);
    }
  };
  custom(availableSelector, 'customAvailable');
  custom(soldOutSelector, 'customSoldOut');

  // The current Naver Booking calendar exposes stable analytics attributes even
  // though its generated CSS-module class suffixes change between deployments.
  const naverDates = [...document.querySelectorAll('[data-click-code="calendar.date"]')]
    .filter(visible);
  const naverTimeRoot = document.querySelector('[data-click-code="calendar.time"]');
  const naverTimes = naverTimeRoot
    ? [...naverTimeRoot.querySelectorAll('button, [role="button"]')].filter(visible)
    : [];
  result.naver.present = naverDates.length > 0 || Boolean(naverTimeRoot);
  const selectedDate = naverDates.find(
    (el) => el.getAttribute('aria-selected') === 'true'
  );
  if (selectedDate) {
    const selectedText = textOf(selectedDate);
    result.naver.selectedDate = {
      text: selectedText.slice(0, 160),
      soldOut: negative.test(selectedText) || disabled(selectedDate) || naverUnselectable(selectedDate)
    };
  }
  result.naver.timeSlots = naverTimes.slice(0, 20).map((el) => ({
    text: textOf(el).slice(0, 160),
    selectable: !disabled(el) && !naverUnselectable(el)
  }));

  const candidates = document.querySelectorAll(
    'button, a, [role="button"], [role="link"], [aria-disabled], [data-testid], time'
  );
  for (const el of candidates) {
    if (!visible(el)) continue;
    const text = textOf(el);
    if (!text || text.length > 160) continue;
    if (negative.test(text)) result.soldOut.push(text);
    const isTab = el.getAttribute('role') === 'tab' || Boolean(el.closest('[role="tablist"]')) ||
      String(el.getAttribute('data-click-code') || '').startsWith('tab.');
    if (actionable(el) && !isTab && !disabled(el) && (positive.test(text) || exactPositive.test(text)) && !positiveExclusion.test(text)) {
      result.available.push(text);
    }
  }

  // A visible sold-out heading/status can be non-actionable. Limit the body scan to
  // exact, short leaf nodes to avoid matching scripts, help text, or hidden templates.
  const leaves = document.querySelectorAll('h1, h2, h3, strong, em, p, span, div[role="status"]');
  for (const el of leaves) {
    if (!visible(el) || el.children.length) continue;
    const text = textOf(el);
    if (text && text.length <= 80 && negative.test(text)) result.soldOut.push(text);
  }
  for (const key of ['customAvailable', 'customSoldOut', 'available', 'soldOut']) {
    result[key] = [...new Set(result[key])].slice(0, 10);
  }
  return result;
}
"""


class ReservationChecker:
    def __init__(self, available_selector: str = "", sold_out_selector: str = "") -> None:
        self.available_selector = available_selector.strip()
        self.sold_out_selector = sold_out_selector.strip()

    def check(self, page: Any) -> DetectionResult:
        try:
            data = page.evaluate(
                DOM_INSPECTION_SCRIPT,
                {
                    "availableSelector": self.available_selector,
                    "soldOutSelector": self.sold_out_selector,
                },
            )
        except Exception as exc:
            return DetectionResult(ReservationState.UNKNOWN, [f"DOM 검사 실패: {exc}"])

        if not isinstance(data, dict):
            return DetectionResult(ReservationState.UNKNOWN, ["DOM 검사 결과 형식 오류"])

        custom_available = self._strings(data.get("customAvailable"))
        custom_sold_out = self._strings(data.get("customSoldOut"))
        available = self._strings(data.get("available"))
        sold_out = self._strings(data.get("soldOut"))
        selector_errors = [
            str(data[key])
            for key in ("customAvailableError", "customSoldOutError")
            if data.get(key)
        ]

        # Explicit user selectors have priority, but contradictory matches remain UNKNOWN.
        if custom_available and not custom_sold_out:
            return DetectionResult(
                ReservationState.AVAILABLE,
                [f"사용자 예약 가능 선택자: {value}" for value in custom_available],
            )
        if custom_sold_out and not custom_available:
            return DetectionResult(
                ReservationState.SOLD_OUT,
                [f"사용자 매진 선택자: {value}" for value in custom_sold_out],
            )
        if custom_available and custom_sold_out:
            return DetectionResult(
                ReservationState.UNKNOWN,
                ["예약 가능/매진 사용자 선택자가 동시에 일치함"],
            )

        # Prefer the inspected Naver calendar/time-slot structure over generic
        # booking words. In particular, the always-enabled "예약하기" tab is not
        # evidence that the selected date has inventory.
        naver = data.get("naver")
        if isinstance(naver, dict) and naver.get("present") is True:
            selected_date = naver.get("selectedDate")
            selected_sold_out = (
                isinstance(selected_date, dict) and selected_date.get("soldOut") is True
            )
            selected_text = (
                str(selected_date.get("text", ""))
                if isinstance(selected_date, dict)
                else ""
            )
            raw_slots = naver.get("timeSlots")
            slots = raw_slots if isinstance(raw_slots, list) else []
            selectable_slots = [
                slot
                for slot in slots
                if isinstance(slot, dict) and slot.get("selectable") is True
            ]
            if selectable_slots and selected_sold_out:
                return DetectionResult(
                    ReservationState.UNKNOWN,
                    ["선택 날짜는 매진이지만 선택 가능한 회차가 함께 표시됨"],
                )
            if selectable_slots:
                names = [str(slot.get("text", "회차")) for slot in selectable_slots]
                return DetectionResult(
                    ReservationState.AVAILABLE,
                    [f"선택 가능한 네이버 회차: {name}" for name in names[:5]],
                )
            if selected_sold_out:
                return DetectionResult(
                    ReservationState.SOLD_OUT,
                    [f"선택 날짜 매진: {selected_text or '매진'}"],
                )
            if slots:
                names = [
                    str(slot.get("text", "회차"))
                    for slot in slots
                    if isinstance(slot, dict)
                ]
                return DetectionResult(
                    ReservationState.SOLD_OUT,
                    [f"선택 불가 네이버 회차: {name}" for name in names[:5]],
                )
            return DetectionResult(
                ReservationState.UNKNOWN,
                ["네이버 예약 달력은 확인했지만 대상 회차 상태가 불명확함"],
            )

        # Enabled, visible booking actions are stronger evidence than informational text.
        if available:
            return DetectionResult(
                ReservationState.AVAILABLE,
                [f"활성 예약 요소: {value}" for value in available],
            )
        if sold_out:
            return DetectionResult(
                ReservationState.SOLD_OUT,
                [f"매진 요소: {value}" for value in sold_out],
            )

        evidence = [f"선택자 오류: {value}" for value in selector_errors]
        evidence.append("신뢰할 수 있는 예약 상태 요소를 찾지 못함")
        return DetectionResult(ReservationState.UNKNOWN, evidence)

    @staticmethod
    def _strings(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]


class AvailabilityTransitionTracker:
    """Track decisive state and trigger only SOLD_OUT -> AVAILABLE transitions."""

    def __init__(self) -> None:
        self.last_decisive: ReservationState | None = None

    def observe(self, current: ReservationState) -> bool:
        if current is ReservationState.UNKNOWN:
            return False
        should_notify = (
            self.last_decisive is ReservationState.SOLD_OUT
            and current is ReservationState.AVAILABLE
        )
        self.last_decisive = current
        return should_notify
