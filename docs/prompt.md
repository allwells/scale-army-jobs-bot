# Scale Army Job Alert Bot — Agent Overview

## What You Are Building

A single-file Python bot that monitors the Scale Army Careers job board at regular intervals and sends new job postings to a Telegram chat. If no new jobs are found during a polling cycle, the bot sends a confirmation message so the user knows it ran successfully.

The script is a **single-run script**: it performs one full polling cycle — fetch, compare, notify — and exits. GitHub Actions is the scheduler. It triggers the script on a cron expression and commits the updated state file back to the repo after each run.

## Deliverables

```
scale-army-jobs-bot/
├── .agent/                ← agent config (already exists)
├── .context.md            ← agent context (already exists)
├── docs/                  ← agent documentation (already exists)
│   └── prompt.md          ← agent prompt (already exists)
├── .github/
│   └── workflows/
│       └── bot.yml        ← GitHub Actions workflow (you create this)
├── main.py                ← entire bot logic (you create this)
├── requirements.txt       ← only: requests (you create this)
├── jobs.json              ← auto-created on first run
├── bot.log                ← auto-created on first run
└── README.md              ← setup and run instructions (you create this)
```

The user runs the bot locally with `python main.py`. In production, GitHub Actions runs it on a cron schedule.

## Data Source

The job board at `https://jobs.ashbyhq.com/Scale%20Army%20Careers` is a JavaScript-rendered SPA — do not scrape it. Ashby exposes a free, unauthenticated public API instead:

```
GET https://api.ashbyhq.com/posting-api/job-board/Scale%20Army%20Careers
```

Response shape:

```json
{
  "jobs": [
    {
      "id": "abc123",
      "title": "Senior Product Manager",
      "location": "Remote",
      "department": "Product",
      "team": "Growth",
      "isRemote": true,
      "employmentType": "FullTime",
      "publishedAt": "2024-11-01T12:00:00.000Z",
      "jobUrl": "https://jobs.ashbyhq.com/Scale%20Army%20Careers/abc123",
      "applyUrl": "https://jobs.ashbyhq.com/Scale%20Army%20Careers/abc123/application"
    }
  ]
}
```

Make a live GET request to verify this shape before writing data-handling code. Use `id` as the unique identifier per job. If `id` is null, fall back to a hash of `title + publishedAt`.

## Hosting: GitHub Actions (Free)

GitHub Actions hosts the bot at zero cost. Each run is an ephemeral Ubuntu VM — no file persists between runs by default. The solution is to store `jobs.json` in the repository itself: the workflow checks it out at the start of each run and commits it back at the end. The script never runs git commands — that is solely the workflow's responsibility.

Secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) are stored in GitHub Secrets and injected as environment variables at runtime. They never appear in any file in the repository.

## Telegram Bot API

Messages are sent via:

```
POST https://api.telegram.org/bot{TOKEN}/sendMessage
```

```json
{
  "chat_id": "...",
  "text": "...",
  "parse_mode": "Markdown",
  "disable_web_page_preview": true
}
```

Telegram Markdown v1 treats `*`, `_`, `` ` ``, and `[` as special characters. Escape these in any API-supplied strings before embedding them in messages or the send will fail with a 400 error.

## First Run Behaviour

If `jobs.json` does not exist when the script runs, record all currently listed jobs as seen without sending any Telegram alerts. Log: `"First run: X existing jobs recorded. Now watching for new postings."` This prevents a flood of notifications for pre-existing jobs.

## Acceptance Criteria

- First run records all existing jobs silently and exits cleanly.
- New jobs trigger a correctly formatted Telegram message within one polling cycle.
- No new jobs triggers a "no new posts" confirmation message.
- Script never crashes from API or Telegram failures.
- Restarting the script never causes duplicate alerts.
- GitHub Actions workflow runs on cron, commits `jobs.json` back, reads credentials from GitHub Secrets only.
