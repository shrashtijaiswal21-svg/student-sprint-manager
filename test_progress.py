import unittest

from app import calculate_progress


class ProgressTests(unittest.TestCase):
    def test_no_tasks_gives_zero_percent(self):
        self.assertEqual(calculate_progress(0, 0), 0)

    def test_half_done(self):
        self.assertEqual(calculate_progress(2, 4), 50)

    def test_all_done(self):
        self.assertEqual(calculate_progress(4, 4), 100)

    def test_percentage_is_rounded_down(self):
        self.assertEqual(calculate_progress(1, 3), 33)


if __name__ == "__main__":
    unittest.main()