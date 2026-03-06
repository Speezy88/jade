#!/usr/bin/env python3
"""
integrations/schoology.py

Fetch upcoming assignments from Schoology ICS feed.
Returns a list of formatted strings for the morning briefing.
Caches results to memory/cache/schoology.json with 6h TTL.
Never raises — returns error list on any failure.
"""

import json
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from icalendar import Calendar

load_dotenv(Path("/Users/spencerhatch/Jade/.env"))

_CACHE_PATH = Path("/Users/spencerhatch/Jade/memory/cache/schoology.json")
_CACHE_TTL  = timedelta(hours=6)
_TZ         = ZoneInfo("America/Los_Angeles")
_ERROR      = ["Schoology unavailable — check manually."]


def _load_cache() -> list[dict] | None:
    """Return cached assignments if fresh (<6h). None if missing or stale."""
    if not _CACHE_PATH.exists():
        return None
    try:
        data = json.loads(_CACHE_PATH.read_text())
        fetched_at = datetime.fromisoformat(data["fetched_at"])
        if datetime.now() - fetched_at < _CACHE_TTL:
            return data["assignments"]
    except Exception:
        pass
    return None


def _save_cache(assignments: list[dict]) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps({
        "fetched_at": datetime.now().isoformat(),
        "assignments": assignments,
    }))


def _parse_dtstart(dtstart_val) -> date | None:
    """Extract a plain date from a DTSTART value (handles date and datetime)."""
    dt = dtstart_val.dt
    if isinstance(dt, datetime):
        return dt.astimezone(_TZ).date()
    if isinstance(dt, date):
        return dt
    return None


def _fetch_assignments() -> list[dict]:
    """Fetch and parse ICS feed. Returns list of {summary, due_date} dicts."""
    url = os.getenv("SCHOOLOGY_ICS_URL", "").strip()
    if not url:
        raise ValueError("SCHOOLOGY_ICS_URL not set in .env")

    # requests cannot handle webcal:// — normalize to https://
    url = url.replace("webcal://", "https://")

    resp = requests.get(url, timeout=10)
    resp.raise_for_status()

    cal   = Calendar.from_ical(resp.content)
    today = date.today()

    assignments = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        dtstart = component.get("DTSTART")
        if not dtstart:
            continue
        due = _parse_dtstart(dtstart)
        if due is None or due < today:
            continue
        summary = str(component.get("SUMMARY", "(no title)"))
        assignments.append({"summary": summary, "due_date": due.isoformat()})

    return assignments


def get_upcoming_assignments() -> list[str]:
    """
    Return assignments due today or tomorrow.

    Returns:
        ["AP History reading — due today", "Math problem set — due tomorrow"]
        [] if fetch succeeds but nothing is due in the next 48h.
        ["Schoology unavailable — check manually."] on missing URL or any error.
    """
    url = os.getenv("SCHOOLOGY_ICS_URL", "").strip()
    if not url:
        print("[schoology] ERROR: SCHOOLOGY_ICS_URL not set in .env", file=sys.stderr)
        return list(_ERROR)

    try:
        assignments = _load_cache()
        if assignments is None:
            assignments = _fetch_assignments()
            _save_cache(assignments)

        today    = date.today()
        tomorrow = today + timedelta(days=1)

        results = []
        for a in assignments:
            due = date.fromisoformat(a["due_date"])
            if due == today:
                results.append(f"{a['summary']} — due today")
            elif due == tomorrow:
                results.append(f"{a['summary']} — due tomorrow")

        return results

    except Exception as exc:
        print(f"[schoology] ERROR: {exc}", file=sys.stderr)
        return list(_ERROR)
