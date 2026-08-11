import datetime as dt
import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "credential_expiry.py"
SPEC = importlib.util.spec_from_file_location("credential_expiry", MODULE_PATH)
assert SPEC and SPEC.loader
credential_expiry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(credential_expiry)


class ReminderStageTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "administrator": "admin",
            "reminder_days": [45, 30, 14, 7, 0],
            "credentials": [
                {
                    "id": "example",
                    "name": "Example credential",
                    "environment": "development",
                    "expires_on": "2026-11-08",
                }
            ],
        }

    def stage_on(self, day: str):
        reminders = credential_expiry.reminders_for(
            self.manifest, dt.date.fromisoformat(day)
        )
        return reminders[0]["stage"] if reminders else None

    def test_no_reminder_before_window(self):
        self.assertIsNone(self.stage_on("2026-09-23"))

    def test_uses_most_recent_crossed_threshold(self):
        self.assertEqual(self.stage_on("2026-09-24"), "45")
        self.assertEqual(self.stage_on("2026-10-09"), "30")
        self.assertEqual(self.stage_on("2026-10-25"), "14")
        self.assertEqual(self.stage_on("2026-11-01"), "7")
        self.assertEqual(self.stage_on("2026-11-08"), "0")

    def test_overdue_stage_is_unique_per_day(self):
        self.assertEqual(self.stage_on("2026-11-09"), "overdue-2026-11-09")


if __name__ == "__main__":
    unittest.main()
