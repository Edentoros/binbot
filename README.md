# binbot 🗑️

A free Telegram reminder for bin day. Every **Tuesday at 21:00 (UK time)** it
messages you which bins go out on Wednesday:

```
🗑️ Bins tomorrow (Wed 4 Nov): ⚫ Black bin + 🟣 Glass bin
```

It runs on GitHub Actions, so there's no server to look after. Collection dates
come from [`schedule.json`](schedule.json); nothing is guessed from a pattern.

| Situation | Message |
| --- | --- |
| Tomorrow is in `schedule.json` | `🗑️ Bins tomorrow (Wed 7 Oct): ⚫ Black bin` |
| Tomorrow is missing | `⚠️ No bin data for tomorrow – update schedule.json with the new council calendar.` |
| 2 or fewer dates left | an extra `📅 Only 2 collection dates left…` line |

## Setup

### 1. Create the Telegram bot

1. In Telegram, open a chat with **@BotFather**.
2. Send `/newbot`, then choose a display name and a username ending in `bot`.
3. BotFather replies with a **token** like `123456789:AAH…`. Treat it like a
   password: anyone with it can control your bot.

### 2. Find your chat ID

1. Open a chat with your new bot and send it any message (e.g. `hi`).
   Bots can't message you until you've messaged them first.
2. In a browser, open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` (replace `<TOKEN>`).
3. Find `"chat":{"id":123456789,…}`. That number is your chat ID.
   If the result is empty, send the bot another message and reload.

### 3. Create the repository

Create a repository on GitHub (private is fine) and push these files to the
default branch (`main`). Scheduled workflows only run from the default branch.

### 4. Add the secrets

In the repository, go to **Settings → Secrets and variables → Actions →
Secrets → New repository secret** and add:

| Name | Value |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | the token from BotFather |
| `TELEGRAM_CHAT_ID` | your chat ID |

### 5. Send a test message

1. Go to **Actions → Bin reminder → Run workflow**.
2. Leave **Test** ticked and click **Run workflow**.
3. Within a minute you should get a message like:

   ```
   🧪 TEST – preview of the reminder for Tue 6 Oct
   🗑️ Bins tomorrow (Wed 7 Oct): ⚫ Black bin
   ```

If **Test** is unticked, a manual run sends the real "bins tomorrow" message
straight away, whatever the time.

If the run fails, open it and check the **Send reminder** step. The usual
causes are a mistyped secret, or not having messaged the bot first.

## Updating the schedule

When the council publishes a new calendar, edit `schedule.json`. Each date is
a Wednesday collection, listing the bins for that day:

```json
{
  "council": "Rushcliffe Borough Council",
  "collections": {
    "2026-12-02": ["Black"],
    "2026-12-09": ["Blue", "Green"]
  }
}
```

Bin names: `Black` ⚫, `Blue` 🔵, `Green` 🟢, `Glass` 🟣. To add a new one, add
it to `BIN_LABELS` in `bin_reminder.py`. You can keep past dates or delete
them; only future ones are used.

## How it works

- **Time zones.** GitHub cron runs in UTC, but 21:00 in London is 20:00 UTC in
  summer (BST) and 21:00 UTC in winter (GMT). The workflow has both crons. The
  script reads `github.event.schedule` to see which one fired and only sends
  if that cron is 21:00 in London on that date. It uses the cron time rather
  than the clock, so a run GitHub starts late still makes the right choice.
- **Keepalive.** GitHub turns off scheduled workflows after 60 days with no
  repository activity. Each Tuesday a small `keepalive` job re-enables the
  workflow through the GitHub API, which resets that timer without dummy
  commits.
- **Reliability.** GitHub doesn't guarantee scheduled runs. They're often a
  few minutes late, and at busy times one can occasionally be dropped.

## Running locally

Python 3.9+; no packages to install.

```sh
python3 -m unittest -v                     # tests
TEST=true python3 bin_reminder.py --dry-run  # print the test message
CRON="0 20 * * 2" python3 bin_reminder.py --dry-run --now 2026-10-06T20:00:00+00:00
```

`--dry-run` prints instead of sending; `--now` pretends it's a different time.
