from __future__ import annotations

import logging
import unittest

from config import AppConfig
from notification import NotificationDispatcher, _apple_script_string


class FakeLocalNotifier:
    def __init__(self):
        self.calls = []

    def show(self, title, message):
        self.calls.append(("show", title, message))

    def play_sound(self):
        self.calls.append(("sound",))


class NotificationTests(unittest.TestCase):
    def test_apple_script_values_are_escaped(self):
        self.assertEqual(_apple_script_string('a"b\\c\nd'), 'a\\"b\\\\c d')

    def test_local_notification_precedes_sound(self):
        config = AppConfig(
            reservation_url="https://booking.naver.com/test",
            macos_notification_enabled=True,
            sound_enabled=True,
            email_enabled=False,
        )
        dispatcher = NotificationDispatcher(config, "", logging.getLogger("test"))
        fake = FakeLocalNotifier()
        dispatcher.local = fake
        dispatcher.notify(config.reservation_url)
        self.assertEqual([call[0] for call in fake.calls], ["show", "sound"])


if __name__ == "__main__":
    unittest.main()
