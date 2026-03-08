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
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

_SCOPES     = ["https://www.googleapis.com/auth/calendar.events"]
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


def _event_color_id(title: str) -> str | None:
    """Return a GCal colorId string based on task type, or None for default."""
    t = title.lower()
    if any(k in t for k in ("act", "math prep", "science prep", "act prep")):
        return "2"   # sage (green)
    if any(k in t for k in ("wellbeing", "think tank", "wtt", "crm", "intern")):
        return "5"   # banana (yellow)
    if any(k in t for k in ("lacrosse", "practice")):
        return "6"   # tangerine (orange)
    return None


def get_events_for_date(target_date: date) -> list[dict]:
    """
    Fetch events for a specific date from all configured calendars.

    Returns:
        List of dicts with keys: id, calendar_id, summary, start_dt, end_dt, all_day.
        start_dt / end_dt are timezone-aware datetimes (America/Los_Angeles).
        all_day events have start_dt=None, end_dt=None.
        Returns [] on any error.
    """
    try:
        service   = _get_service()
        day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=_TZ)
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
                for e in result.get("items", []):
                    start   = e["start"]
                    end     = e.get("end", {})
                    all_day = "date" in start and "dateTime" not in start
                    if all_day:
                        start_dt = end_dt = None
                    else:
                        start_dt = datetime.fromisoformat(start["dateTime"]).astimezone(_TZ)
                        end_dt   = (datetime.fromisoformat(end["dateTime"]).astimezone(_TZ)
                                    if "dateTime" in end else None)
                    all_events.append({
                        "id":          e.get("id", ""),
                        "calendar_id": cal_id,
                        "summary":     e.get("summary", "(no title)"),
                        "start_dt":    start_dt,
                        "end_dt":      end_dt,
                        "all_day":     all_day,
                    })
            except Exception as exc:
                print(f"[gcal] WARNING: could not fetch {cal_id}: {exc}", file=sys.stderr)

        all_events.sort(key=lambda e: e["start_dt"] or day_start)
        return all_events

    except Exception as exc:
        print(f"[gcal] ERROR: {exc}", file=sys.stderr)
        return []


def create_event(
    title: str,
    start_dt: datetime,
    end_dt: datetime,
    description: str = "",
    calendar_id: str = "spencerchatch@gmail.com",
) -> str | None:
    """
    Write a time-blocked event to Google Calendar.

    Returns:
        The created event id on success, None on failure (logs error, never raises).
    """
    try:
        service = _get_service()
        body: dict = {
            "summary": title,
            "start":   {"dateTime": start_dt.isoformat(), "timeZone": "America/Los_Angeles"},
            "end":     {"dateTime": end_dt.isoformat(),   "timeZone": "America/Los_Angeles"},
        }
        if description:
            body["description"] = description
        color_id = _event_color_id(title)
        if color_id:
            body["colorId"] = color_id
        event = service.events().insert(calendarId=calendar_id, body=body).execute()
        return event.get("id")
    except Exception as exc:
        print(f"[gcal] ERROR creating event '{title}': {exc}", file=sys.stderr)
        return None


def delete_jade_events_for_date(target_date: date) -> int:
    """
    Delete all Jade-created blocks for target_date from the personal calendar.
    Identifies Jade events by description starting with "jade:".
    Returns count of deleted events. Never raises.
    """
    try:
        service   = _get_service()
        day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=_TZ)
        day_end   = day_start + timedelta(days=1)
        cal_id    = "spencerchatch@gmail.com"

        result = service.events().list(
            calendarId=cal_id,
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
        ).execute()

        deleted = 0
        for e in result.get("items", []):
            if e.get("description", "").startswith("jade:"):
                try:
                    service.events().delete(calendarId=cal_id, eventId=e["id"]).execute()
                    deleted += 1
                except Exception as exc:
                    print(f"[gcal] WARNING: could not delete '{e.get('summary')}': {exc}",
                          file=sys.stderr)
        return deleted

    except Exception as exc:
        print(f"[gcal] ERROR in delete_jade_events_for_date: {exc}", file=sys.stderr)
        return 0


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
