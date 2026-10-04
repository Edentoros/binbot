import unittest
from datetime import date, datetime, timezone

import bin_reminder as br

BST_CRON = "0 19 * * 2"
GMT_CRON = "0 20 * * 2"


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def london_send_time(cron, now):
    return br.scheduled_instant(cron, now).astimezone(br.LONDON)


class CronTest(unittest.TestCase):
    def test_summer_uses_19_utc(self):
        now = utc(2026, 10, 6, 19, 3)  # Tue 6 Oct, BST
        self.assertEqual(london_send_time(BST_CRON, now).hour, 20)

    def test_summer_skips_20_utc(self):
        now = utc(2026, 10, 6, 20, 2)
        self.assertEqual(london_send_time(GMT_CRON, now).hour, 21)

    def test_winter_uses_20_utc(self):
        now = utc(2026, 11, 3, 20, 1)  # Tue 3 Nov, GMT
        self.assertEqual(london_send_time(GMT_CRON, now).hour, 20)

    def test_winter_skips_19_utc(self):
        now = utc(2026, 11, 3, 19, 1)
        self.assertEqual(london_send_time(BST_CRON, now).hour, 19)

    def test_late_start_still_uses_scheduled_time(self):
        # The 19:00 UTC run starts 75 minutes late, after the 20:00 one was due.
        now = utc(2026, 10, 6, 20, 15)
        self.assertEqual(br.scheduled_instant(BST_CRON, now), utc(2026, 10, 6, 19, 0))

    def test_very_late_start_past_midnight(self):
        now = utc(2026, 11, 4, 0, 30)  # Wednesday, 4.5h late
        local = london_send_time(GMT_CRON, now)
        self.assertEqual((local.date(), local.hour), (date(2026, 11, 3), 20))

    def test_rejects_unsupported_cron(self):
        with self.assertRaises(ValueError):
            br.scheduled_instant("*/5 * 1 * *", utc(2026, 10, 6, 20, 0))


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


class ScheduleFileTest(unittest.TestCase):
    def test_schedule_json_is_valid(self):
        schedule = br.load_schedule()
        self.assertTrue(schedule)
        for day, bins in schedule.items():
            for b in bins:
                self.assertIn(b, br.BIN_LABELS, f"{day}: unknown bin {b!r}")


if __name__ == "__main__":
    unittest.main()
