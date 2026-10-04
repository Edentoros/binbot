#!/usr/bin/env python3
"""Send a Telegram reminder about tomorrow's bin collection.

Runs on GitHub Actions. Standard library only.

Environment:
  TELEGRAM_BOT_TOKEN  Bot token from @BotFather (required unless --dry-run).
  TELEGRAM_CHAT_ID    Chat to send to (required unless --dry-run).
  CRON                The cron expression that triggered the run
                      (github.event.schedule). Empty for manual runs.
  TEST                "true" to send a test message for the next collection.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

LONDON = ZoneInfo("Europe/London")
SEND_TIME_LOCAL = (21, 0)  # 21:00 in London
LOW_DATES_THRESHOLD = 2
SCHEDULE_PATH = Path(__file__).with_name("schedule.json")

BIN_LABELS = {
    "Black": "⚫ Black bin",
    "Blue": "🔵 Blue bin",
    "Green": "🟢 Green bin",
    "Glass": "🟣 Glass bin",
}

NO_DATA_MESSAGE = (
    "⚠️ No bin data for tomorrow – update schedule.json with the new council calendar."
)


def load_schedule(path=SCHEDULE_PATH):
    """Return {date: [bin, ...]} from schedule.json."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)["collections"]
    schedule = {}
    for day, bins in raw.items():
        if not isinstance(bins, list) or not bins:
            raise ValueError(f"schedule.json: {day} must have a non-empty list of bins")
        schedule[date.fromisoformat(day)] = bins
    return schedule


def fmt_day(d):
    return f"{d:%a} {d.day} {d:%b}"  # e.g. "Wed 7 Oct"


def bin_label(name):
    return BIN_LABELS.get(name, f"🗑️ {name} bin")


def build_message(schedule, today):
    """The reminder sent on `today` (London date) about tomorrow's bins."""
    tomorrow = today + timedelta(days=1)
    bins = schedule.get(tomorrow)
    if bins is None:
        return NO_DATA_MESSAGE

    lines = [f"🗑️ Bins tomorrow ({fmt_day(tomorrow)}): "
             + " + ".join(bin_label(b) for b in bins)]

    remaining = sorted(d for d in schedule if d >= tomorrow)
    if len(remaining) <= LOW_DATES_THRESHOLD:
        n = len(remaining)
        lines.append(
            f"📅 Only {n} collection date{'s' if n != 1 else ''} left in schedule.json "
            f"(last: {fmt_day(remaining[-1])}) – time to add the new council calendar."
        )
    return "\n".join(lines)


def build_test_message(schedule, today):
    """Preview of the next real reminder, labelled as a test."""
    upcoming = sorted(d for d in schedule if d > today)
    if not upcoming:
        return "🧪 TEST\n" + NO_DATA_MESSAGE
    send_day = upcoming[0] - timedelta(days=1)
    return (f"🧪 TEST – preview of the reminder for {fmt_day(send_day)}\n"
            + build_message(schedule, send_day))


def scheduled_instant(cron, now):
    """Most recent UTC datetime <= now that matches `cron`.

    Only handles the simple form "M H * * DOW" (DOW may be "*"), which is
    all this workflow uses. Working from the cron rather than the clock
    keeps the result right even if GitHub starts the run late.
    """
    fields = cron.split()
    if len(fields) != 5 or fields[2:4] != ["*", "*"]:
        raise ValueError(f"Unsupported cron expression: {cron!r}")
    minute, hour, dow = int(fields[0]), int(fields[1]), fields[4]
    # Cron counts Sunday as 0 (or 7); Python counts Monday as 0.
    weekday = None if dow == "*" else (int(dow) + 6) % 7

    for days_back in range(8):
        d = (now - timedelta(days=days_back)).date()
        candidate = datetime(d.year, d.month, d.day, hour, minute, tzinfo=timezone.utc)
        if candidate <= now and (weekday is None or candidate.weekday() == weekday):
            return candidate
    raise ValueError(f"No time matching {cron!r} in the week before {now}")


def send_telegram(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=30) as resp:
            body = json.load(resp)
    except urllib.error.HTTPError as e:
        # Report Telegram's error description without leaking the token in the URL.
        try:
            detail = json.load(e).get("description", "")
        except ValueError:
            detail = ""
        raise SystemExit(f"Telegram API error {e.code}: {detail}") from None
    except urllib.error.URLError as e:
        raise SystemExit(f"Could not reach Telegram: {e.reason}") from None
    if not body.get("ok"):
        raise SystemExit(f"Telegram API error: {body.get('description', body)}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="print the message instead of sending it")
    parser.add_argument("--now", type=datetime.fromisoformat,
                        help="pretend the current time is this (ISO 8601, with offset)")
    args = parser.parse_args(argv)

    now = (args.now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    cron = os.environ.get("CRON", "").strip()
    test = os.environ.get("TEST", "").strip().lower() == "true"
    schedule = load_schedule()

    if test:
        text = build_test_message(schedule, now.astimezone(LONDON).date())
    elif cron:
        local = scheduled_instant(cron, now).astimezone(LONDON)
        if (local.hour, local.minute) != SEND_TIME_LOCAL:
            print(f"Skipping: cron {cron!r} is {local:%H:%M %Z} in London on "
                  f"{local:%a %d %b %Y}; the other cron covers 21:00.")
            return 0
        text = build_message(schedule, local.date())
    else:
        # Manual run without the test flag: send the real reminder for tomorrow now.
        text = build_message(schedule, now.astimezone(LONDON).date())

    print(text)
    if args.dry_run:
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise SystemExit("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set.")
    send_telegram(token, chat_id, text)
    print("Sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
