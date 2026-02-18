---
name: send-telegram-message
description: Send formatted Telegram messages via the Bot HTTP API using requests. Use when implementing Telegram notifications, message formatting, Markdown escaping, or retry logic.
---

## Implementation

```python
import requests
import logging
import time

def send_telegram_message(text: str, token: str, chat_id: str) -> bool:
    """
    Send a Markdown message to Telegram. Retries once on failure.
    Returns True on success, False otherwise. Never raises.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    for attempt in range(2):
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            if attempt == 0:
                logging.warning(f"Telegram send failed (attempt 1): {e}. Retrying in 5s...")
                time.sleep(5)
            else:
                logging.error(f"Telegram send failed after retry: {e}. Message dropped.")
                return False
    return False


def escape_markdown(text: str) -> str:
    """Escape Telegram Markdown v1 special characters in API-supplied strings."""
    for char in ["*", "_", "`", "["]:
        text = text.replace(char, f"\\{char}")
    return text


def format_new_job_message(job: dict) -> str:
    title      = escape_markdown(job["title"])
    department = escape_markdown(job["department"])
    team       = escape_markdown(job["team"])
    location   = escape_markdown(job["location"])
    emp_type   = escape_markdown(job["employment_type"])
    remote_tag = " (Remote)" if job["is_remote"] else ""
    pub_date   = job["published_at"][:10] if job["published_at"] else "Unknown"
    dept_line  = f"{department} › {team}" if team else department

    return (
        f"🆕 *New Job Alert*\n\n"
        f"*{title}*\n"
        f"🏢 {dept_line}\n"
        f"📍 {location}{remote_tag}\n"
        f"💼 {emp_type}\n"
        f"📅 Published: {pub_date}\n\n"
        f"🔗 [View Job]({job['job_url']})\n"
        f"✅ [Apply Now]({job['apply_url']})"
    )


def format_no_new_jobs_message(timestamp: str) -> str:
    return (
        f"🔍 Checked Scale Army Careers — no new jobs posted.\n"
        f"🕐 Checked at: {timestamp}"
    )
```

## Key Notes

- `disable_web_page_preview: True` prevents noisy link preview cards when sending multiple job messages
- Telegram Markdown v1 only treats `*`, `_`, `` ` ``, `[` as special — escape these in all API-supplied strings
- Slice `publishedAt[:10]` for a readable `YYYY-MM-DD` date with no extra dependencies
- One retry only — Telegram is reliable; hammering it won't help
