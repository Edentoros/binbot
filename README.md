# binbot 🗑️

A free Telegram reminder for bin day. Every **Tuesday at 20:00 (UK time)** it
messages you which bins go out on Wednesday:

```
⚫ Black and 🟣 Glass bins tomorrow!
```

It runs on GitHub Actions, so there's no server to look after. A free
[cron-job.org](https://cron-job.org) job starts it at 20:00 UK time on Tuesdays.
Collection dates come from [`schedule.json`](schedule.json); nothing is guessed
from a pattern.

| Situation | Message |
| --- | --- |
| Tomorrow is in `schedule.json` | `⚫ Black bin tomorrow!` |
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
default branch (`main`).

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
   ⚫ Black bin tomorrow!
   ```

If **Test** is unticked, a manual run sends the real "… tomorrow!" message
straight away, whatever the time.

If the run fails, open it and check the **Send reminder** step. The usual
causes are a mistyped secret, or not having messaged the bot first.

### 6. Create a GitHub token for the timer

The timer starts the workflow through GitHub's API, so it needs a token that
can do that and nothing else.

1. On GitHub, go to **Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token**.
2. Name it e.g. `binbot-timer` and pick an expiry. When it expires the
   reminders stop, so put a note in your calendar to renew it.
3. **Repository access:** *Only select repositories* → this repository.
4. **Permissions → Repository permissions → Actions:** *Read and write*.
   Leave everything else as it is.
5. Generate it and copy the token. It goes straight into cron-job.org in the
   next step; don't store it anywhere else.

### 7. Set up the timer on cron-job.org

1. Sign up at [cron-job.org](https://cron-job.org) (free) and create a cron job.
2. **URL** (replace `OWNER/REPO`):
   `https://api.github.com/repos/OWNER/REPO/actions/workflows/bin-reminder.yml/dispatches`
3. **Schedule:** custom, **Tuesday at 20:00**, time zone **Europe/London**.
   Using the London time zone means summer and winter time are handled for you.
4. In the advanced settings:
   - **Request method:** `POST`
   - **Headers:**

     | Header | Value |
     | --- | --- |
     | `Accept` | `application/vnd.github+json` |
     | `Authorization` | `Bearer <your token>` |
     | `X-GitHub-Api-Version` | `2022-11-28` |
     | `Content-Type` | `application/json` |

   - **Request body:** `{"ref":"main","inputs":{"test":"false"}}`
5. Turn on the email notification for failed runs, so you hear about an
   expired token.
6. **Test it:** change the body's `"false"` to `"true"`, use cron-job.org's
   test run, and check that GitHub answers `204` and the 🧪 test message
   arrives. Then set it back to `"false"` and save. (A test run with
   `"false"` on any day but Tuesday sends the "No bin data for tomorrow"
   warning, which is correct but confusing.)

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

- **Why an external timer.** GitHub's own `schedule` trigger only queues runs
  when it has spare capacity: the first scheduled reminder here started almost
  four hours late. Runs started through the API (`workflow_dispatch`) begin
  within seconds, so cron-job.org does the timing and GitHub does the work.
- **Time zones.** cron-job.org fires at 20:00 Europe/London, and the script
  takes "tomorrow" from the London date, so BST and GMT need no special
  handling.
- **No keepalive needed.** GitHub's 60-day auto-disable only applies to
  workflows with a `schedule` trigger, and this one has none.

## Running locally

Python 3.9+; no packages to install.

```sh
python3 -m unittest -v                     # tests
TEST=true python3 bin_reminder.py --dry-run  # print the test message
python3 bin_reminder.py --dry-run --now 2026-10-06T19:00:00+00:00  # Tue 20:00 BST
```

`--dry-run` prints instead of sending; `--now` pretends it's a different time.
