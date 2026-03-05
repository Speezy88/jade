# /timeblock
# Place at: ~/Jade/.claude/commands/timeblock.md
# Usage: /timeblock  OR  /timeblock today  OR  /timeblock "tomorrow afternoon"
# Tier 1 use — Spencer types this regularly

Generate a time-blocked schedule for available calendar windows.
Uses live Google Calendar data and Spencer's personal task duration model.

---

## EXECUTION SEQUENCE

**1. Fetch live calendar data.**
```bash
python integrations/gcal.py --hours 48    # next 48h to handle tomorrow requests
```
Do not generate time blocks without confirmed calendar state.

**2. Identify available windows.**
- Parse existing events as hard blocks (cannot move)
- Identify gaps of 20+ minutes as potential work windows
- Respect known fixed blocks: school 8:15am–3pm, lacrosse 4:30–7pm (in-season)
- Flag recovery time after lacrosse as low-intensity only (reading, light review — not deep work)

**3. Load task queue.**
Read in priority order:
- Open items from `memory/WORK/` with approaching deadlines
- Schoology assignments due within 48h → `memory/cache/schoology.json`
- Open GitHub issues marked high priority
- Items surfaced in most recent `/brief`

**4. Load time model (if available).**
```python
# memory/time_model/model.json
# Use median_min for each task type
# Use confidence level to add buffer:
#   high confidence → +10% buffer
#   medium → +20% buffer
#   low → +30% buffer
```

If no time model data exists for a task type, use conservative defaults and note it:
- Math problem set → 75 min (default, no personal data yet)
- Essay work → 60 min (default)
- Reading → 30 min/chapter (default)

**5. Generate the time-blocked schedule.**

Format per block:
```
[TIME] – [DURATION] → [TASK]
         Estimate basis: [personal median / default]
         Why now: [brief rationale — urgency, cognitive load match, dependency]
```

Example:
```
12:55pm – 50 min → AP History reading (Ch. 9-10)
          Estimate: 28 min/chapter × 2 = 56 min, blocking 50 (high confidence)
          Why now: free period, low cognitive load, due tomorrow

8:00pm – 75 min → Math problem set (Ch. 7 derivatives)
          Estimate: 74 min median (12 samples, high confidence)
          Why now: longest focused window of evening, hardest task first
```

**6. Propose calendar writes.**
After presenting the schedule, ask:
"Write these blocks to Google Calendar? [yes / adjust / skip]"

If yes → call `integrations/gcal.py --write` with the proposed blocks.
If adjust → accept Spencer's modifications, then write.
If skip → save the proposed schedule to `memory/WORK/timeblock-YYYYMMDD.md` for reference.

**7. Do not over-schedule.**
Leave at least one 20-minute unblocked window per evening for unexpected tasks.
Do not schedule deep work (essay, math) in the 30 minutes immediately after lacrosse.

---

## ESCALATION
If the schedule is impossible — too many high-priority tasks for available windows — say so directly:
"Three high-priority tasks, 2.5 hours of available time. Something doesn't fit. Which drops?"
Present the trade-off. Do not silently omit tasks.
