from __future__ import annotations

import unittest

from reservation_checker import (
    AvailabilityTransitionTracker,
    ReservationChecker,
    ReservationState,
)


class FakePage:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.arguments = None

    def evaluate(self, _script, arguments):
        self.arguments = arguments
        if self.error:
            raise self.error
        return self.result


class ReservationCheckerTests(unittest.TestCase):
    def test_naver_sold_out_calendar_beats_booking_tab_text(self):
        page = FakePage(
            {
                "customAvailable": [],
                "customSoldOut": [],
                "naver": {
                    "present": True,
                    "selectedDate": {"text": "15 매진", "soldOut": True},
                    "timeSlots": [{"text": "오후 2:00", "selectable": False}],
                },
                "available": ["예약하기"],
                "soldOut": ["15 매진"],
            }
        )
        result = ReservationChecker().check(page)
        self.assertEqual(result.state, ReservationState.SOLD_OUT)

    def test_selectable_naver_time_slot_is_available(self):
        page = FakePage(
            {
                "naver": {
                    "present": True,
                    "selectedDate": {"text": "15", "soldOut": False},
                    "timeSlots": [{"text": "오후 2:00", "selectable": True}],
                }
            }
        )
        result = ReservationChecker().check(page)
        self.assertEqual(result.state, ReservationState.AVAILABLE)
        self.assertIn("오후 2:00", result.evidence[0])

    def test_contradictory_naver_signals_are_unknown(self):
        page = FakePage(
            {
                "naver": {
                    "present": True,
                    "selectedDate": {"text": "15 매진", "soldOut": True},
                    "timeSlots": [{"text": "오후 2:00", "selectable": True}],
                }
            }
        )
        result = ReservationChecker().check(page)
        self.assertEqual(result.state, ReservationState.UNKNOWN)

    def test_enabled_booking_action_is_available(self):
        page = FakePage(
            {
                "customAvailable": [],
                "customSoldOut": [],
                "available": ["예약하기"],
                "soldOut": ["다른 날짜 매진"],
            }
        )
        result = ReservationChecker().check(page)
        self.assertEqual(result.state, ReservationState.AVAILABLE)

    def test_sold_out_without_available_action(self):
        page = FakePage(
            {
                "customAvailable": [],
                "customSoldOut": [],
                "available": [],
                "soldOut": ["예약 마감"],
            }
        )
        result = ReservationChecker().check(page)
        self.assertEqual(result.state, ReservationState.SOLD_OUT)

    def test_no_evidence_is_unknown(self):
        result = ReservationChecker().check(FakePage({}))
        self.assertEqual(result.state, ReservationState.UNKNOWN)

    def test_dom_failure_is_unknown(self):
        result = ReservationChecker().check(FakePage(error=RuntimeError("changed")))
        self.assertEqual(result.state, ReservationState.UNKNOWN)
        self.assertIn("DOM 검사 실패", result.evidence[0])

    def test_conflicting_custom_selectors_are_unknown(self):
        result = ReservationChecker(".open", ".closed").check(
            FakePage(
                {
                    "customAvailable": ["open"],
                    "customSoldOut": ["closed"],
                    "available": [],
                    "soldOut": [],
                }
            )
        )
        self.assertEqual(result.state, ReservationState.UNKNOWN)

    def test_selectors_are_forwarded_to_dom_script(self):
        page = FakePage({})
        ReservationChecker(".open", ".closed").check(page)
        self.assertEqual(page.arguments["availableSelector"], ".open")
        self.assertEqual(page.arguments["soldOutSelector"], ".closed")


class TransitionTrackerTests(unittest.TestCase):
    def test_initial_available_does_not_notify(self):
        tracker = AvailabilityTransitionTracker()
        self.assertFalse(tracker.observe(ReservationState.AVAILABLE))

    def test_only_sold_out_to_available_notifies(self):
        tracker = AvailabilityTransitionTracker()
        states = [
            ReservationState.SOLD_OUT,
            ReservationState.SOLD_OUT,
            ReservationState.AVAILABLE,
            ReservationState.AVAILABLE,
        ]
        self.assertEqual([tracker.observe(state) for state in states], [False, False, True, False])

    def test_unknown_preserves_last_decisive_state(self):
        tracker = AvailabilityTransitionTracker()
        self.assertFalse(tracker.observe(ReservationState.SOLD_OUT))
        self.assertFalse(tracker.observe(ReservationState.UNKNOWN))
        self.assertTrue(tracker.observe(ReservationState.AVAILABLE))

    def test_repeated_cycles_can_notify_again(self):
        tracker = AvailabilityTransitionTracker()
        states = [
            ReservationState.SOLD_OUT,
            ReservationState.AVAILABLE,
            ReservationState.SOLD_OUT,
            ReservationState.AVAILABLE,
        ]
        self.assertEqual([tracker.observe(state) for state in states], [False, True, False, True])


if __name__ == "__main__":
    unittest.main()
