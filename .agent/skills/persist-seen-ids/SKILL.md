---
name: persist-seen-ids
description: Load and save the set of seen job IDs to a local JSON file. Use when implementing first-run detection, ID diffing, or the write-before-notify persistence pattern.
---

## Why This Works on GitHub Actions

Each GitHub Actions runner is ephemeral — files don't survive between runs. `jobs.json` is stored in the repository itself. The workflow checks it out at run start and commits it back at run end. The script just reads/writes a local file; it never runs git commands.

## Implementation

```python
import json
import logging
import os

def load_seen_ids(filepath: str) -> tuple[set, bool]:
    """
    Returns (ids: set, is_first_run: bool).
    is_first_run=True when the file doesn't exist — caller suppresses notifications.
    Corrupted file → log warning, return empty set, is_first_run=False.
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
    Write seen IDs to disk immediately.
    CALL THIS BEFORE SENDING TELEGRAM MESSAGES.
    If the script crashes mid-send, IDs are already persisted — no duplicates on restart.
    """
    try:
        data = {"ids": sorted(list(ids))}
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        logging.error(f"Failed to save seen IDs: {e}")
```

## First Run Logic

```python
seen_ids, is_first_run = load_seen_ids(JOBS_FILE)
jobs = fetch_jobs()
current_ids = {job["id"] for job in jobs}

if is_first_run:
    # Record everything silently — no Telegram alerts for pre-existing jobs
    save_seen_ids(current_ids, JOBS_FILE)
    logging.info(f"First run: {len(current_ids)} existing jobs recorded. Watching for new postings.")
    return

# Normal cycle
new_ids = current_ids - seen_ids
```

## Write-Before-Notify Pattern

Always: `save_seen_ids()` → then `send_telegram_message()`.
A missed notification (crash after write, before send) is acceptable.
A duplicate notification (crash before write, IDs re-announced next run) is not.
