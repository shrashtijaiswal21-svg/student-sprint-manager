import unittest
from datetime import date

from app import days_until, deadline_label


class DeadlineTests(unittest.TestCase):
    def test_days_until_future_date(self):
        self.assertEqual(days_until("2026-10-11", today=date(2026, 10, 8)), 3)

    def test_days_until_today_is_zero(self):
        self.assertEqual(days_until("2026-10-08", today=date(2026, 10, 8)), 0)

    def test_days_until_past_date_is_negative(self):
        self.assertEqual(days_until("2026-10-05", today=date(2026, 10, 8)), -3)

    def test_label_far_deadline_is_green(self):
        self.assertEqual(deadline_label(10), ("Ends in 10 days", "success"))

    def test_label_close_deadline_is_warning(self):
        self.assertEqual(deadline_label(2), ("Ends in 2 days", "warning"))

    def test_label_one_day_left(self):
        self.assertEqual(deadline_label(1), ("Ends in 1 day", "warning"))

    def test_label_ends_today(self):
        self.assertEqual(deadline_label(0), ("Ends today", "danger"))

    def test_label_overdue(self):
        self.assertEqual(deadline_label(-2), ("Overdue by 2 days", "danger"))


if __name__ == "__main__":
    unittest.main()