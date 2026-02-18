"""
Scale Army Job Alert Bot
------------------------
Single-run script: fetch → diff → notify → exit.
GitHub Actions is the scheduler. jobs.json is committed back to the repo
after each run to persist state across ephemeral runners.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Load .env file for local development if it exists
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

# To add more boards, just append to this list:
BOARDS = [
    {
        "name": "Scale Army Careers",
        "url": "https://api.ashbyhq.com/posting-api/job-board/Scale%20Army%20Careers"
    },
]

JOBS_FILE = "jobs.json"
LOG_FILE = "bot.log"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# ---------------------------------------------------------------------------
# Ashby API
# ---------------------------------------------------------------------------

def fetch_jobs(board: dict) -> list[dict]:
    """
    Fetch all current jobs from a specific Ashby public API board.
    Returns a normalised list of job dicts, or [] on any failure.
    """
    url = board["url"]
    name = board["name"]
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        raw_jobs = data.get("jobs", [])
        return [normalise_job(job, name) for job in raw_jobs if isinstance(job, dict)]
    except requests.exceptions.Timeout:
        logging.error(f"Ashby API timed out for {name}.")
        return []
    except requests.exceptions.HTTPError as e:
        logging.error(f"Ashby API HTTP error for {name}: {e.response.status_code}")
        return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error fetching jobs for {name}: {e}")
        return []
    except (ValueError, KeyError) as e:
        logging.error(f"Failed to parse Ashby response for {name}: {e}")
        return []


def normalise_job(raw: dict, platform_name: str) -> dict:
    employment_type_map = {
        "FullTime": "Full-Time",
        "PartTime": "Part-Time",
        "Contract": "Contract",
        "Intern": "Internship",
    }
    raw_type = raw.get("employmentType", "")
    # Fallback ID: deterministic string so we can still track the job if id is null
    job_id = raw.get("id") or f"{raw.get('title', '')}_{raw.get('publishedAt', '')}"
    
    # We prefix ID with platform for global uniqueness across multiple boards
    internal_id = f"{platform_name}:{job_id}"
    
    return {
        "id":              internal_id,
        "platform":        platform_name,
        "title":           raw.get("title", "Untitled Role"),
        "department":      raw.get("department", "Unknown"),
        "team":            raw.get("team", ""),
        "location":        raw.get("location", "Unknown"),
        "is_remote":       raw.get("isRemote", False),
        "employment_type": employment_type_map.get(raw_type, raw_type),
        "published_at":    raw.get("publishedAt", ""),
        "job_url":         raw.get("jobUrl", ""),
        "apply_url":       raw.get("applyUrl", ""),
    }

# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def load_seen_ids(filepath: str) -> tuple[set, bool]:
    """
    Returns (ids: set, is_first_run: bool).
    is_first_run=True when the file doesn't exist — caller suppresses notifications.
    A corrupted file is treated as a non-first run with an empty set.
    """
    if not os.path.exists(filepath):
        return set(), True  # Genuine first run

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("ids", [])), False
    except (json.JSONDecodeError, IOError) as e:
        logging.warning(f"Could not read {filepath}: {e}. Starting with empty seen-IDs.")
        return set(), False


def save_seen_ids(ids: set, filepath: str) -> None:
    """
    Write the current set of seen IDs to disk.
    Always call this BEFORE sending Telegram messages (write-before-notify pattern).
    If the script crashes mid-send, IDs are already persisted — no duplicates on restart.
    """
    try:
        data = {"ids": sorted(list(ids))}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        logging.error(f"Failed to save seen IDs to {filepath}: {e}")

# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

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
    platform   = escape_markdown(job["platform"])
    title      = escape_markdown(job["title"])
    department = escape_markdown(job["department"])
    team       = escape_markdown(job["team"])
    location   = escape_markdown(job["location"])
    emp_type   = escape_markdown(job["employment_type"])
    remote_tag = " (Remote)" if job["is_remote"] else ""
    pub_date   = job["published_at"][:10] if job["published_at"] else "Unknown"
    dept_line  = f"{department} › {team}" if team else department

    return (
        f"🆕 *New Job Alert* on {platform}\n\n"
        f"*{title}*\n"
        f"🏢 {dept_line}\n"
        f"📍 {location}{remote_tag}\n"
        f"💼 {emp_type}\n"
        f"📅 Published: {pub_date}\n\n"
        f"🔗 [View Job]({job['job_url']})\n"
        f"✅ [Apply Now]({job['apply_url']})"
    )



# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # Validate credentials at startup — fail fast with a clear message
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise SystemExit(
            "ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set as environment variables."
        )

    logging.info("Starting Multi-Board Job Alert Bot...")

    # 1. Load persisted state
    seen_ids, is_first_run = load_seen_ids(JOBS_FILE)

    # 2. Fetch current jobs from all Ashby boards
    all_jobs = []
    platforms_checked = []
    
    for board in BOARDS:
        logging.info(f"Fetching jobs for {board['name']}...")
        board_jobs = fetch_jobs(board)
        if board_jobs:
            all_jobs.extend(board_jobs)
            platforms_checked.append(board["name"])

    if not all_jobs:
        logging.warning("No jobs returned from any board. Skipping this cycle.")
        return

    current_ids = {job["id"] for job in all_jobs}
    job_by_id   = {job["id"]: job for job in all_jobs}

    # 3. First run: record all existing jobs silently, no Telegram alerts
    if is_first_run:
        save_seen_ids(current_ids, JOBS_FILE)
        logging.info(
            f"First run: {len(current_ids)} existing jobs recorded across "
            f"{len(platforms_checked)} platform(s). Now watching for new postings."
        )
        return

    # 4. Diff: find new and removed jobs
    new_ids     = current_ids - seen_ids
    removed_ids = seen_ids - current_ids

    # 5. Update seen IDs: add new, remove stale (write-before-notify)
    updated_ids = (seen_ids | new_ids) - removed_ids
    save_seen_ids(updated_ids, JOBS_FILE)

    if removed_ids:
        logging.info(f"{len(removed_ids)} job(s) removed from the boards.")

    # 6. Send Telegram alerts for new jobs
    from datetime import timedelta
    tz = timezone(timedelta(hours=1))
    timestamp = datetime.now(tz).strftime("%a %b %d, %Y at %I:%M %p")

    if new_ids:
        logging.info(f"{len(new_ids)} new job(s) found. Sending Telegram alerts...")
        # Sort by ID or title for consistent ordering in notifications
        for job_id in sorted(list(new_ids)):
            job = job_by_id[job_id]
            message = format_new_job_message(job)
            success = send_telegram_message(message, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
            if success:
                logging.info(f"Notified: [{job['platform']}] {job['title']} ({job_id})")
    else:
        logging.info("No new jobs found during this cycle.")

    logging.info("Run complete.")


if __name__ == "__main__":
    main()
