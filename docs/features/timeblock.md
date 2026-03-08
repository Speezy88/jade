# timeblock.md — Calendar Time-Blocking Feature
*Phase 2 | Status: Complete and operational*

---

## What It Does

Generates a Haiku-proposed time-blocked schedule from live Google Calendar data and
nightly context, presents it for review with an adjustment loop, then writes confirmed
blocks to Google Calendar. Triggered on-demand via `/timeblock` or automatically after
the nightly check-in.

## Entry Point

`jade_timeblock.py`

```bash
python3 jade_timeblock.py          # block tomorrow (default)
python3 jade_timeblock.py --today  # block today
```

## Call Sequence

```
jade_timeblock.py
  ├── get_events_for_date(target_date) → raw event dicts
  ├── _load_nightly_context()          → priorities, intentions, task_durations
  ├── _load_morning_context()          → schedule_additions, focus (if today)
  ├── get_upcoming_assignments()       → Schoology items
  ├── _compute_free_windows()          → free windows ≥25 min
  ├── build_timeblock_system_prompt()  → SOUL + GOALS + BRIEFING_TONE + context + TIMEBLOCK_INSTRUCTIONS
  ├── Haiku call (max_tokens=4096)     → JSON schedule proposal
  ├── Print proposal
  ├── Adjustment loop (max 3 rounds)
  │     Spencer types edit → Haiku returns updated JSON → reprint
  ├── On confirm: create_event() for each non-unscheduled block
  ├── _log_overrides()                 → duration_signals.jsonl (one line per change)
  └── _write_timeblock_log()           → memory/logs/timeblock/YYYY-MM-DD.json
```

## Free Window Computation

`_compute_free_windows(events, target_date)`:
- Hard-blocks school 8:15am–3:00pm on weekdays (unless a school event already covers it)
- Applies 15-min buffer on either side of any event ≥60 min
- Adds 30-min post-event buffer for lacrosse/practice events
- Excludes before 7:00am and after 10:30pm
- Returns only gaps ≥25 min

## JSON Schema (Haiku output)

```json
{
  "blocks": [
    {"title": "", "start_iso": "", "end_iso": "", "duration_min": 0, "basis": "", "rationale": ""}
  ],
  "unscheduled_windows": [
    {"start_iso": "", "end_iso": "", "duration_min": 0}
  ],
  "conflicts": []
}
```

Blocks with `"unscheduled"` in the title are skipped at write time (display only).

## Revise Flow

If `memory/logs/timeblock/YYYY-MM-DD.json` already exists for the target date:
1. Jade asks "Already blocked — revise?"
2. On confirm: `delete_jade_events_for_date()` removes prior Jade blocks from GCal
3. Schedule is rebuilt from scratch

## Duration Signal Logging

Every adjusted block appends to `memory/logs/duration_signals.jsonl`:
```json
{"date": "YYYY-MM-DD", "task": "...", "estimated_min": 90, "actual_min": 120, "source": "timeblock_override"}
```
This file seeds the Phase 5.5 time model.

## Outputs

- GCal events on `spencerchatch@gmail.com`
- `memory/logs/timeblock/YYYY-MM-DD.json` — run log
- `memory/logs/duration_signals.jsonl` — override signals (append-only)

## Post-Nightly Trigger

`jade_nightly.py` ends Phase E with:
```
Want me to block tomorrow? [yes / skip]
```
On confirm → `subprocess.run(["python3", "jade_timeblock.py"])`.
Declining closes nightly cleanly with no side effects.
