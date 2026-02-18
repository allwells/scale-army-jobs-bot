# Scale Army Job Alert Bot

A lightweight Python bot that monitors the [Scale Army Careers](https://jobs.ashbyhq.com/Scale%20Army%20Careers) job board and sends Telegram alerts whenever new jobs are posted. Hosted for free on GitHub Actions.

---

## How It Works

1. **GitHub Actions** triggers the bot on a cron schedule (every 30 minutes by default).
2. The bot fetches all current jobs from the Ashby public API.
3. It compares the current listings against `jobs.json` (the persisted state file stored in this repo).
4. **New jobs** → one Telegram message per new posting.
5. **No new jobs** → a short confirmation message so you know the bot ran.
6. **Removed jobs** → pruned from `jobs.json` silently (no notification).
7. The updated `jobs.json` is committed back to the repo so state persists across runs.

### First Run

If `jobs.json` doesn't exist yet, the bot records all current jobs silently — no Telegram alerts. This prevents a flood of notifications for pre-existing listings.

---

## Prerequisites

- Python 3.8+
- A Telegram bot token and chat ID (see below)
- Python 3.8+
- A Telegram bot token and chat ID (see below)
- A GitHub repository with Actions enabled

---

## Local Setup

### Method 1: Standard

```bash
# Clone the repo
git clone https://github.com/allwells/scale-army-jobs-bot.git
cd scale-army-jobs-bot

# Install the single dependency
pip install -r requirements.txt

# Set your credentials in .env
# You can copy the template: cp .env.template .env
# Then edit .env with your token and chat ID

# Run the bot
python main.py
```

### Method 2: Virtual Environment (Recommended)

If you encounter `ModuleNotFoundError` or have multiple Python versions installed, use a virtual environment:

```bash
# Create the environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install and run
pip install -r requirements.txt
python main.py
```

On first run, `jobs.json` and `bot.log` are created automatically.

---

## Getting Telegram Credentials

### Bot Token

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot` and follow the prompts.
3. Copy the token (format: `7412345678:AAFxyz...`).

### Chat ID

1. Start a conversation with your new bot (send it any message).
2. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in your browser.
3. Find `"chat": {"id": ...}` in the response — that number is your chat ID.
4. For a group chat, add the bot to the group first; the chat ID will be a negative number.

---

## GitHub Actions Setup (Free Hosting)

### 1. Add Secrets

Go to your repository on GitHub:  
**Settings → Secrets and Variables → Actions → New repository secret**

Add two secrets:

| Name                 | Value                         |
| -------------------- | ----------------------------- |
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |
| `TELEGRAM_CHAT_ID`   | Your chat ID                  |

### 2. Push the Workflow

The workflow file is already at `.github/workflows/bot.yml`. Push it to your repo and GitHub Actions will pick it up automatically.

### 3. Trigger Manually (Optional)

Go to **Actions → Scale Army Job Alert Bot → Run workflow** to trigger a run immediately without waiting for the cron.

### Changing the Schedule

Edit the `cron` expression in `.github/workflows/bot.yml`:

```yaml
- cron: "*/30 * * * *" # Every 30 minutes
- cron: "0 * * * *" # Every hour (default)
- cron: "0 */2 * * *" # Every 2 hours
```

> **Note:** GitHub's cron scheduler can be delayed 5–15 minutes under load. This is normal and acceptable for a job alert bot.

---

## File Structure

```
scale-army-jobs-bot/
├── .github/
│   └── workflows/
│       └── bot.yml        ← GitHub Actions workflow
├── main.py                ← All bot logic
├── requirements.txt       ← requests only
├── jobs.json              ← Auto-created; committed by the workflow
└── bot.log                ← Auto-created; local run log
```

---

## Credentials Security

- Secrets are stored in GitHub Secrets and injected as environment variables at runtime.
- They are **never** written to any file in the repository.
- `jobs.json` contains only job IDs — no sensitive data.
