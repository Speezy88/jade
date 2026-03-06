# gcal_integration.md — Google Calendar Integration
*Phase 1 | Status: Complete*

---

## Function

`get_today_events()` in `integrations/gcal.py`

Returns a sorted list of today's events from all configured calendars.
Format: `"9:00 AM — Math class"` (timed) or `"All day — No School"` (all-day).
Returns `[]` on zero events or any error. Never raises.

## Calendars

```python
_CALENDARS = ["spencerchatch@gmail.com", "spencerhatch@seattleacademy.org"]
```

Both calendars are fetched independently. If one fails, the error is logged to stderr
and skipped — the other calendar's events are still returned.

## Auth

- **Type:** OAuth 2.0 (not API key)
- **Scope:** `https://www.googleapis.com/auth/calendar.readonly`
- **Credentials:** `~/.config/jade/credentials.json` (never committed)
- **Token:** `~/.config/jade/token.json` (auto-generated on first run)
- **First run:** Opens browser for auth flow. Must be done manually before loading launchd plist.
- **Token refresh:** Automatic when expired, if refresh token exists.

## Time Handling

- Google API returns UTC datetimes — all converted to `America/Los_Angeles` before display
- All-day events have `date` field (not `dateTime`) — handled separately
- Time format: `"%-I:%M %p"` → `"9:00 AM"` (macOS/Linux only)
- Query window: today midnight → tomorrow midnight (LA time)

## Phase 2 Upgrade Required

Phase 2 (time-blocking) needs write access. To upgrade scope:
1. Delete `~/.config/jade/token.json`
2. Update `_SCOPES` in `gcal.py` to include `calendar.events`
3. Re-run auth flow: `python3 -c "from integrations.gcal import get_today_events; get_today_events()"`

## Known Issue

`spencerhatch@seattleacademy.org` is a Google Workspace account separate from Gmail.
If events aren't appearing, verify the school calendar is shared with the Gmail account,
or that the OAuth credentials belong to an account with access to both.
