---
name: github-actions-deploy
description: Create the GitHub Actions workflow file that schedules the bot, injects secrets, and commits jobs.json back to the repo after each run. Use when creating bot.yml or configuring free hosting on GitHub Actions.
---

## Workflow File

Create at `.github/workflows/bot.yml`:

```yaml
name: Scale Army Job Alert Bot

on:
  schedule:
    # Adjust cron to change frequency. Common values:
    # Every 30 min: '*/30 * * * *'   Every hour: '0 * * * *'
    # Every 2 hrs:  '0 */2 * * *'    Every 6hrs: '0 */6 * * *'
    - cron: "*/30 * * * *"
  workflow_dispatch: # Allows manual trigger from GitHub Actions UI for testing

jobs:
  check-jobs:
    runs-on: ubuntu-latest

    # REQUIRED: without this, git push at the end returns 403 Forbidden
    permissions:
      contents: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        # Pulls jobs.json from the repo onto the runner filesystem

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run the bot
        env:
          # Secrets are stored in GitHub → Settings → Secrets and Variables → Actions
          # They are never stored in code or committed to the repo
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python main.py

      - name: Commit updated jobs.json
        run: |
          git config user.name "Job Alert Bot"
          git config user.email "bot@noreply.github.com"
          git add jobs.json
          # Only commit if file actually changed — without this guard, git commit
          # exits non-zero when nothing changed, which fails the workflow run
          git diff --staged --quiet || git commit -m "chore: update seen job IDs"
          git push
```

## Reading Secrets in main.py

```python
import os

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

# Validate at startup — fail fast with a clear message rather than a cryptic API error
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise SystemExit("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set as environment variables.")
```

## Critical Details

| Issue                           | Cause                                              | Fix                                                               |
| ------------------------------- | -------------------------------------------------- | ----------------------------------------------------------------- |
| `git push` returns 403          | Missing write permission                           | Add `permissions: contents: write` to the job                     |
| Workflow fails when no new jobs | `git commit` exits non-zero with nothing to commit | Use `git diff --staged --quiet \|\|` guard before commit          |
| Secrets appear in logs          | Wrong injection method                             | Always use `${{ secrets.NAME }}` in `env:` block, never echo them |

## Adding Secrets in GitHub

Settings → Secrets and Variables → Actions → New repository secret.
Add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` as separate secrets.

## Cron Accuracy Note

GitHub's cron scheduler can be delayed 5–15 minutes under load. This is normal and acceptable for a job alert bot.
