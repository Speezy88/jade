# Phase 2 Spec — Calendar Time-Blocking
*File: docs/features/phase2-spec.md*
*Status: DRAFT — Pending Spencer approval before Plan Mode*

---

## 1. What / Why

Phase 2 takes everything Jade knows about tomorrow — priorities from the nightly, intentions Spencer stated, existing calendar constraints, goal commitments from ACTIVE_GOALS.md — and writes a real time-blocked schedule into Google Calendar.

The morning briefing tells Spencer what the day looks like. Phase 2 makes the day look like what it should. Without it, Jade is an information system. With it, Jade is an execution system.

---

## 2. Trigger

Two entry points, one engine:

| Trigger | When | How |
|--------|------|-----|
| Post-nightly | End of Phase E in `jade_nightly.py` | Jade asks: "Want me to block tomorrow?" — Spencer confirms, `jade_timeblock.py` runs in same terminal |
| On-demand | Any time | `/timeblock` slash command → `jade_timeblock.py` |

`jade_timeblock.py` is always a standalone script. `jade_nightly.py` calls it via `subprocess` or direct import after Spencer confirms. This keeps the files cleanly separated and `/timeblock` independently functional.

---

## 3. Inputs

| Source | Data | How accessed |
|--------|------|-------------|
| `memory/cache/tomorrow_context.json` | Priorities, stated intentions, open loops | Direct file read |
| `memory/cache/morning_context.json` | Same-day adjustments if running via `/timeblock` during the day | Direct file read — optional, skip if stale |
| `integrations/gcal.py` | Existing events for target day (hard constraints) | `get_today_events()` — will add `get_events_for_date(date)` |
| `memory/ACTIVE_GOALS.md` | Goal domains + stated time commitments ("30 min/day ACT") | File read + Haiku parsing |
| `memory/logs/duration_signals.jsonl` | Historical duration overrides for calibration | File read — optional, skip if missing |

---

## 4. Duration Model

Two tiers. No new config file.

**Tier 1 — Fixed (from ACTIVE_GOALS.md):**
Haiku parses ACTIVE_GOALS.md for explicit time commitments at prompt time. Examples:
- "30 minutes/day" → ACT block = 30 min
- "Weekly prep commitment: 30 minutes/day" → same

These are treated as floors, not ceilings. Spencer can override up or down.

**Tier 2 — Estimated (everything else):**
Haiku estimates duration for tasks without a stated commitment and states its reasoning inline:

```
ACT Math prep — 30 min (from your stated commitment)
CRM UI update — 90 min (estimated: UI work with defined scope usually runs 60–120 min)
College list research — 45 min (estimated: research task, low friction)
```

Spencer can override any estimate before blocks are written.

**Override logging:**
Every override appends one line to `memory/logs/duration_signals.jsonl`:
```json
{"date": "2026-03-07", "task": "CRM UI update", "estimated_min": 90, "actual_min": 120, "source": "nightly_override"}
```
No schema, no model, no new system. Phase 5.5 reads this file when it builds the duration model. Cost today: 1 line of code.

---

## 5. Scheduling Logic

Jade builds the schedule in this order:

1. **Plot hard constraints** — existing GCal events are immovable (lacrosse practice, school, meetings)
2. **Identify free windows** — gaps between hard constraints, accounting for travel/transition time (15 min buffer on either side of any event > 1 hour)
3. **Rank tasks by priority** — from `tomorrow_context.json` priorities list, weighted by goal stakes from ACTIVE_GOALS.md
4. **Fit tasks into windows** — highest priority task gets first available window of sufficient size. No task is split across windows in Phase 2 (deferred to Phase 5.5)
5. **Apply constraints** — ACT prep never scheduled after 9pm. No blocks during lacrosse. Minimum block size: 25 min (below this, Jade skips and notes it)
6. **Produce proposal** — printed to terminal, not written to GCal yet

Jade does not fill every minute. Unscheduled time is not a failure — it is noted as available.

---

## 6. Proposal Format

Printed to terminal before any GCal write:

```
Tomorrow — Sunday, March 8

Blocked:
  9:00 AM – 10:30 AM   Wellbeing Think Tank — CRM UI update (90 min, estimated)
  10:30 AM – 11:00 AM  ACT Math prep (30 min, commitment)
  11:00 AM – 11:45 AM  College list research (45 min, estimated)

Hard constraints (already on calendar):
  4:30 PM – 7:00 PM    Lacrosse practice

Unscheduled:
  11:45 AM – 4:30 PM   ~285 min open (lunch, buffer, or add tasks below)

Does this look right? Hit enter to confirm, or type changes (e.g. "CRM 2 hours", "move ACT to 2pm", "add dentist 1pm 30 min"):
```

Spencer responds in natural language. Jade parses the response, adjusts the proposal, reprints it, confirms again. Max 3 rounds before writing — if still unresolved, Jade writes as-is and notes what was unclear.

Natural language edits are handled as a structured Haiku call: current proposal passed as JSON + Spencer's edit string → Haiku returns updated proposal as JSON. No regex parsing.

---

## 7. GCal Write

After confirmation:

- Each block written as a GCal event via `integrations/gcal.py` (expanded to write scope)
- Event title: task name only — no Jade branding, no metadata in title
- Event description: `jade: {task_type} | est: {duration_min}min | source: {priority|intention|manual}`
- Calendar: `spencerchatch@gmail.com` (personal — not school calendar)
- Color: consistent per task type (ACT = one color, WTT = another) — Phase 2 picks reasonable defaults, Spencer can override in Phase 3
- On failure: log to stderr, notify, do not crash — same pattern as all integrations

---

## 8. Implementation

### New files
- `jade_timeblock.py` — standalone script, entry point for all timeblocking

### Modified files
- `integrations/gcal.py` — add `get_events_for_date(date)` + `create_event(title, start, end, description, calendar_id)` — write scope requires OAuth re-auth (delete `~/.config/jade/token.json`, re-auth with `calendar.events` scope)
- `jade_nightly.py` — add post-Phase-E prompt: "Want me to block tomorrow?" + subprocess call to `jade_timeblock.py` on confirm
- `jade_prompts.py` — add `build_timeblock_system_prompt(context)` — same assembly pattern

### New log files
- `memory/logs/duration_signals.jsonl` — override signal capture
- `memory/logs/timeblock/YYYY-MM-DD.json` — what was proposed, what was written, any delta

### OAuth hard constraint
`gcal.py` currently has `calendar.readonly` scope. Phase 2 requires `calendar.events`.
Before any code is written:
```bash
rm ~/.config/jade/token.json
python3 -c "from integrations.gcal import get_today_events; get_today_events()"
```
Re-auth in browser with expanded scope. Verify both read and write work before building.

---

## 9. Edge Cases

| Scenario | Behavior |
|----------|----------|
| `tomorrow_context.json` missing or stale | Jade falls back to ACTIVE_GOALS.md only — blocks goal commitments into open windows, notes that nightly context is absent |
| No free windows (fully booked day) | Jade reports this explicitly: "Tomorrow is fully booked — no room to add blocks without moving something." Does not write anything. |
| Spencer declines post-nightly prompt | Nothing runs. No file written. Nightly closes normally. |
| `/timeblock` run same day as nightly | Dedup check: if `memory/logs/timeblock/YYYY-MM-DD.json` exists, Jade asks "Already blocked today — want to revise?" before proceeding |
| GCal write fails on one event | Log error, continue writing remaining events, report failures at end |
| Spencer mentions a duration in natural language during nightly ("I need like 2 hours for the CRM thing") | `extract_structured()` in nightly captures this in `tomorrow_context.json` under `task_durations: {task: min}` — timeblock reads it as Tier 1 |

---

## 10. ISC — Integration Success Criteria

Phase 2 is complete when all of the following pass:

- [ ] **ISC-1:** OAuth re-auth completed with `calendar.events` scope — read and write both verified
- [ ] **ISC-2:** `jade_timeblock.py` runs standalone via `/timeblock` and produces a valid proposal
- [ ] **ISC-3:** Proposal correctly excludes existing GCal events as hard constraints
- [ ] **ISC-4:** ACT prep block duration matches ACTIVE_GOALS.md stated commitment (30 min)
- [ ] **ISC-5:** Haiku estimates for non-fixed tasks include stated reasoning
- [ ] **ISC-6:** Spencer can override duration in natural language and proposal updates correctly
- [ ] **ISC-7:** Override appends one line to `duration_signals.jsonl` with correct schema
- [ ] **ISC-8:** Confirmed blocks appear in Google Calendar within 30 seconds of confirmation
- [ ] **ISC-9:** GCal events have correct title, description metadata, and land on personal calendar only
- [ ] **ISC-10:** Post-nightly prompt ("Want me to block tomorrow?") triggers `jade_timeblock.py` on confirm
- [ ] **ISC-11:** Declining post-nightly prompt closes nightly cleanly with no side effects
- [ ] **ISC-12:** `memory/logs/timeblock/YYYY-MM-DD.json` written after every successful run
- [ ] **ISC-13:** SOUL.md tone holds — proposal reads like Jade, not a calendar app

---

## 11. Out of Scope (Phase 2)

- Task splitting across windows (Phase 5.5)
- Duration model / adaptive estimation (Phase 5.5 — `duration_signals.jsonl` seeds it)
- Color customization beyond defaults (Phase 3)
- Schoology assignment auto-scheduling (Phase 3 — needs duration signals first)
- Mobile push of finalized schedule (later phase)
- ROG/MSI routing (Phase 9)

---

## 12. Files Touched

| File | Action |
|------|--------|
| `jade_timeblock.py` | Create |
| `jade_prompts.py` | Update — add `build_timeblock_system_prompt(context)` |
| `integrations/gcal.py` | Update — add `get_events_for_date()` + `create_event()`, re-auth for write scope |
| `jade_nightly.py` | Update — post-Phase-E confirmation prompt + subprocess call |
| `memory/logs/duration_signals.jsonl` | Auto-created on first override |
| `memory/logs/timeblock/` | Create directory |
| `docs/CHANGELOG.md` | Update |
| `docs/PROJECT_STATUS.md` | Update |

---

*Proposed updates surface via /retro. Spencer approves before any change is committed.*
