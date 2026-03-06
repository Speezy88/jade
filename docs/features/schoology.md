# schoology.md — Schoology Integration
*Phase 1 | Status: Complete*

---

## Function

`get_upcoming_assignments()` in `integrations/schoology.py`

Returns assignments due today or tomorrow. Caches results 6h to reduce feed hits
and handle the ~6h lag between teacher posts and ICS feed updates.

## Return Values

| Scenario | Return |
|----------|--------|
| Assignments due in 48h | `["AP History reading — due today", "Calc HW — due tomorrow"]` |
| No assignments due | `[]` |
| URL missing from .env | `["Schoology unavailable — check manually."]` |
| Fetch error / parse error | `["Schoology unavailable — check manually."]` |

## Cache

- **Path:** `memory/cache/schoology.json`
- **TTL:** 6 hours
- **Schema:** `{"fetched_at": "2026-03-06T07:00:00", "assignments": [{"summary": "...", "due_date": "2026-03-06"}]}`
- **Cache stores all future events** — filtering to today/tomorrow happens at call time,
  so the cache remains valid across midnight without a re-fetch

## URL Format

The `.env` entry must use `https://`, not `webcal://`:
```
SCHOOLOGY_ICS_URL=https://seattleacademy.schoology.com/calendar/feed/ical/.../ical.ics
```
The code normalizes `webcal://` → `https://` as a fallback, but the `.env` entry should be correct.

## Date Handling

- Filters out events with DTSTART before today (past events fill the full ICS export)
- Handles both `date` (date-only) and `datetime` (with time) DTSTART values
- All datetimes converted to `America/Los_Angeles` before date comparison

## Known Behavior

- Feed lags ~6h after teachers post — expected, not a bug
- Schoology ICS includes the full academic calendar, not just upcoming items — the past-event filter is required
- Grades are not in the ICS feed — grade data is out of scope
