#!/usr/bin/env python3
"""
integrations/gcal.py

Fetch today's Google Calendar events (America/Los_Angeles).
Returns a list of formatted strings for the morning briefing.
Never raises — returns [] on any error.

First run triggers browser OAuth flow and writes ~/.config/jade/token.json.
Subsequent runs auto-refresh token if expired.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

_SCOPES     = ["https://www.googleapis.com/auth/calendar.readonly"]
_CREDS_PATH = Path.home() / ".config" / "jade" / "credentials.json"
_TOKEN_PATH = Path.home() / ".config" / "jade" / "token.json"
_TZ         = ZoneInfo("America/Los_Angeles")
_CALENDARS  = ["spencerchatch@gmail.com", "spencerhatch@seattleacademy.org"]


def _get_service():
    """Build an authorized Google Calendar service. Triggers browser auth on first run."""
    creds = None

    if _TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN_PATH), _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(_CREDS_PATH), _SCOPES)
            creds = flow.run_local_server(port=0)
        _TOKEN_PATH.write_text(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def _format_event(event: dict) -> str:
    """Format a single calendar event as a display string."""
    title = event.get("summary", "(no title)")
    start = event["start"]

    if "dateTime" in start:
        dt = datetime.fromisoformat(start["dateTime"]).astimezone(_TZ)
        time_str = dt.strftime("%-I:%M %p")  # "9:00 AM"
        return f"{time_str} — {title}"

    # All-day event (date only, no time)
    return f"All day — {title}"


def _sort_key(event: dict) -> datetime:
    """Return a timezone-aware datetime for sorting. All-day events sort to midnight."""
    start = event["start"]
    if "dateTime" in start:
        return datetime.fromisoformat(start["dateTime"]).astimezone(_TZ)
    # All-day: parse date string, treat as midnight LA
    d = datetime.strptime(start["date"], "%Y-%m-%d")
    return d.replace(tzinfo=_TZ)


def get_today_events() -> list[str]:
    """
    Fetch today's events from all configured calendars, merged and sorted by start time.

    Returns:
        List of formatted strings, e.g. ["9:00 AM — Math class", "All day — No School"].
        Empty list if no events or any error occurs.
    """
    try:
        service = _get_service()

        now_la    = datetime.now(_TZ)
        day_start = now_la.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end   = day_start + timedelta(days=1)

        all_events: list[dict] = []
        for cal_id in _CALENDARS:
            try:
                result = service.events().list(
                    calendarId=cal_id,
                    timeMin=day_start.isoformat(),
                    timeMax=day_end.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                ).execute()
                all_events.extend(result.get("items", []))
            except Exception as exc:
                print(f"[gcal] WARNING: could not fetch {cal_id}: {exc}", file=sys.stderr)

        all_events.sort(key=_sort_key)
        return [_format_event(e) for e in all_events]

    except Exception as exc:
        print(f"[gcal] ERROR: {exc}", file=sys.stderr)
        return []
