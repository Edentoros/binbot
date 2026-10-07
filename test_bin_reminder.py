import contextlib
import io
import os
import unittest
from datetime import date
from unittest import mock

import bin_reminder as br

# Fixed copy of the autumn 2026 calendar so these tests don't change when
# schedule.json is updated.
SCHEDULE = {
    date(2026, 10, 7): ["Black"],
    date(2026, 10, 14): ["Blue", "Green"],
    date(2026, 10, 21): ["Black"],
    date(2026, 10, 28): ["Blue", "Green"],
    date(2026, 11, 4): ["Black", "Glass"],
    date(2026, 11, 11): ["Blue", "Green"],
    date(2026, 11, 18): ["Black"],
    date(2026, 11, 25): ["Blue", "Green"],
}


class MessageTest(unittest.TestCase):
    def setUp(self):
        self.schedule = SCHEDULE

    def test_single_bin(self):
        self.assertEqual(br.build_message(self.schedule, date(2026, 10, 6)),
                         "⚫ Black bin tomorrow!")

    def test_two_bins(self):
        self.assertEqual(br.build_message(self.schedule, date(2026, 11, 3)),
                         "⚫ Black and 🟣 Glass bins tomorrow!")

    def test_black_and_green(self):
        schedule = {date(2026, 12, 2): ["Black", "Green"]}
        self.assertEqual(br.build_message(schedule, date(2026, 12, 1)).splitlines()[0],
                         "⚫ Black and 🟢 Green bins tomorrow!")

    def test_three_bins(self):
        schedule = {date(2026, 12, 2): ["Black", "Blue", "Green"]}
        self.assertEqual(br.build_message(schedule, date(2026, 12, 1)).splitlines()[0],
                         "⚫ Black, 🔵 Blue and 🟢 Green bins tomorrow!")

    def test_no_data(self):
        self.assertEqual(br.build_message(self.schedule, date(2026, 12, 1)),
                         br.NO_DATA_MESSAGE)

    def test_no_reminder_with_three_dates_left(self):
        msg = br.build_message(self.schedule, date(2026, 11, 10))
        self.assertNotIn("📅", msg)

    def test_reminder_with_two_dates_left(self):
        msg = br.build_message(self.schedule, date(2026, 11, 17))
        self.assertEqual(msg.splitlines()[1],
                         "📅 Only 2 collection dates left in schedule.json "
                         "(last: Wed 25 Nov) – time to add the new council calendar.")

    def test_reminder_with_last_date(self):
        msg = br.build_message(self.schedule, date(2026, 11, 24))
        self.assertIn("Only 1 collection date left", msg)

    def test_test_message_previews_next_collection(self):
        msg = br.build_test_message(self.schedule, date(2026, 10, 4))
        self.assertEqual(msg, "🧪 TEST – preview of the reminder for Tue 6 Oct\n"
                              "⚫ Black bin tomorrow!")

    def test_test_message_after_schedule_ends(self):
        msg = br.build_test_message(self.schedule, date(2026, 12, 1))
        self.assertIn(br.NO_DATA_MESSAGE, msg)


class MainTest(unittest.TestCase):
    """main() picks 'tomorrow' from the London date, whatever UTC says."""

    def run_main(self, now, test="false"):
        out = io.StringIO()
        with mock.patch.object(br, "load_schedule", return_value=SCHEDULE), \
                mock.patch.dict(os.environ, {"TEST": test}), \
                contextlib.redirect_stdout(out):
            br.main(["--dry-run", "--now", now])
        return out.getvalue().strip()

    def test_tuesday_evening_summer(self):
        # 20:00 BST is 19:00 UTC.
        self.assertEqual(self.run_main("2026-10-06T19:00:00+00:00"),
                         "⚫ Black bin tomorrow!")

    def test_tuesday_evening_winter(self):
        # 20:00 GMT is 20:00 UTC.
        self.assertEqual(self.run_main("2026-11-03T20:00:00+00:00"),
                         "⚫ Black and 🟣 Glass bins tomorrow!")

    def test_test_mode(self):
        self.assertTrue(self.run_main("2026-10-07T12:00:00+00:00", test="true")
                        .startswith("🧪 TEST – preview of the reminder for Tue 13 Oct"))


class ScheduleFileTest(unittest.TestCase):
    def test_schedule_json_is_valid(self):
        schedule = br.load_schedule()
        self.assertTrue(schedule)
        for day, bins in schedule.items():
            for b in bins:
                self.assertIn(b, br.BIN_LABELS, f"{day}: unknown bin {b!r}")


if __name__ == "__main__":
    unittest.main()
