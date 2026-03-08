# gcal_integration.md — Google Calendar Integration
*Phase 1–2 | Status: Complete (read + write)*

---

## Functions

| Function | Returns | Used by |
|----------|---------|---------|
| `get_today_events()` | `list[str]` — formatted event strings | jade_briefing.py, jade_nightly.py |
| `get_events_for_date(target_date)` | `list[dict]` — raw event dicts with `start_dt`, `end_dt`, `all_day` | jade_timeblock.py |
| `create_event(title, start_dt, end_dt, description)` | `str \| None` — created event id | jade_timeblock.py |
| `delete_jade_events_for_date(target_date)` | `int` — count deleted | jade_timeblock.py (revise flow) |

All functions never raise — log errors to stderr and return safe defaults.

## Calendars

```python
_CALENDARS = ["spencerchatch@gmail.com", "spencerhatch@seattleacademy.org"]
```

Read: both calendars. Write: `spencerchatch@gmail.com` only.
Jade events are identified by `description.startswith("jade:")`.

## Auth

- **Type:** OAuth 2.0 (not API key)
- **Scope:** `https://www.googleapis.com/auth/calendar.events` (read + write)
- **Credentials:** `~/.config/jade/credentials.json` (never committed)
- **Token:** `~/.config/jade/token.json` (auto-generated on first run)
- **First run:** Opens browser for auth flow. Must be done manually before loading launchd plist.
- **Token refresh:** Automatic when expired, if refresh token exists.

## Event Colors

`_event_color_id(title)` returns a GCal colorId based on title keywords:
- ACT/math prep/science prep → `"2"` (sage/green)
- Wellbeing/WTT/CRM/intern → `"5"` (banana/yellow)
- Lacrosse/practice → `"6"` (tangerine/orange)
- Default → no color override

## Time Handling

- All datetimes converted to `America/Los_Angeles` (`_TZ`)
- All-day events: `start_dt = end_dt = None`, `all_day = True`
- Time format for display: `"%-I:%M %p"` → `"9:00 AM"` (macOS/Linux only)

## Known Issue

`spencerhatch@seattleacademy.org` is a Google Workspace account separate from Gmail.
If events aren't appearing, verify the school calendar is shared with the Gmail account,
or that the OAuth credentials belong to an account with access to both.
