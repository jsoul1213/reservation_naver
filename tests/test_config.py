from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from config import AppConfig, load_config, save_config


class AppConfigTests(unittest.TestCase):
    def test_valid_naver_booking_configuration(self):
        config = AppConfig(reservation_url="https://booking.naver.com/booking/12/bizes/34")
        self.assertEqual(config.validate(), [])

    def test_rejects_non_naver_url_and_short_interval(self):
        config = AppConfig(reservation_url="https://example.com", check_interval=1.0)
        errors = config.validate()
        self.assertEqual(len(errors), 2)

    def test_email_requires_delivery_settings(self):
        config = AppConfig(
            reservation_url="https://m.place.naver.com/place/123/booking",
            email_enabled=True,
        )
        self.assertTrue(any("수신 주소" in error for error in config.validate()))
        self.assertTrue(any("SMTP" in error for error in config.validate()))

    def test_round_trip_ignores_unknown_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "reservation_url": "https://naver.me/abc",
                        "check_interval": 5,
                        "future_option": True,
                    }
                ),
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config.check_interval, 5)
            save_config(config, path)
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("future_option", stored)

    def test_numeric_strings_are_normalized(self):
        config = AppConfig.from_dict(
            {"check_interval": "4.5", "smtp_port": "587", "settle_time_ms": "800"}
        )
        self.assertEqual(config.check_interval, 4.5)
        self.assertEqual(config.smtp_port, 587)
        self.assertEqual(config.settle_time_ms, 800)


if __name__ == "__main__":
    unittest.main()
