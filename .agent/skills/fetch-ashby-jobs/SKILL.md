---
name: fetch-ashby-jobs
description: Fetch and normalise job listings from the Ashby public API for Scale Army Careers. Use when implementing the API call, parsing job data, or handling API failure modes.
---

## API Endpoint

```
GET https://api.ashbyhq.com/posting-api/job-board/Scale%20Army%20Careers
```

No authentication required. Plain `requests.get()` works.

## Implementation

```python
import requests
import logging

ASHBY_API_URL = "https://api.ashbyhq.com/posting-api/job-board/Scale%20Army%20Careers"

def fetch_jobs() -> list[dict]:
    """
    Fetch all current jobs from Ashby API.
    Returns normalised list of job dicts, or empty list on any failure.
    """
    try:
        response = requests.get(ASHBY_API_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        raw_jobs = data.get("jobs", [])
        return [normalise_job(job) for job in raw_jobs if isinstance(job, dict)]

    except requests.exceptions.Timeout:
        logging.error("Ashby API timed out.")
        return []
    except requests.exceptions.HTTPError as e:
        logging.error(f"Ashby API error: {e.response.status_code}")
        return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error: {e}")
        return []
    except (ValueError, KeyError) as e:
        logging.error(f"Failed to parse Ashby response: {e}")
        return []


def normalise_job(raw: dict) -> dict:
    employment_type_map = {
        "FullTime": "Full-Time",
        "PartTime": "Part-Time",
        "Contract": "Contract",
        "Intern": "Internship",
    }
    raw_type = raw.get("employmentType", "")
    # Fallback ID: if API omits `id`, build a deterministic one so we can still track the job
    job_id = raw.get("id") or f"{raw.get('title', '')}_{raw.get('publishedAt', '')}"
    return {
        "id":              job_id,
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
```

## Edge Cases Handled

- API timeout (15s limit)
- Non-200 HTTP responses
- Network unreachable
- Malformed JSON
- Null or missing `id` field
- Unknown `employmentType` values
