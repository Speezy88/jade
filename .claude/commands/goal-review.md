# /goal-review
# Place at: ~/Jade/.claude/commands/goal-review.md
# Usage: /goal-review
# Tier 2 use — run weekly, Sunday recommended

Weekly execution gap analysis. Reads signal data and goal progress.
Surfaces where Spencer is on track and where execution is lagging behind intent.

---

## WHEN TO RUN
Sunday evening, or any time a goal feels like it's drifting.
Do not run more than once per week — the signal window is weekly by design.

---

## EXECUTION SEQUENCE

**1. Set the review window.**
```python
from datetime import date, timedelta
end = date.today()
start = end - timedelta(days=7)
```

**2. Read goal state.**
```python
# memory/goals/ACTIVE_GOALS.md — current stated goals
# memory/goals/college_app/PLAN.md — if exists
# memory/goals/wellbeing_internship/PLAN.md — if exists
# memory/goals/jade_build/PLAN.md — if exists
```

**3. Read signal data for this week.**
```python
import json
from pathlib import Path

signals = []
signals_file = Path("memory/LEARNING/SIGNALS/ratings.jsonl")
if signals_file.exists():
    for line in signals_file.read_text().strip().split("\n"):
        if line:
            entry = json.loads(line)
            if start.isoformat() <= entry["date"] <= end.isoformat():
                signals.append(entry)

weekly_avg = sum(s["rating"] for s in signals) / len(signals) if signals else None
low_ratings = [s for s in signals if s["rating"] <= 4]
```

**4. Read time model data for the week.**
```python
import csv
from pathlib import Path

log_path = Path("memory/time_model/manual_log.csv")
week_entries = []
if log_path.exists():
    with open(log_path) as f:
        for row in csv.DictReader(f):
            if start.isoformat() <= row["date"] <= end.isoformat():
                week_entries.append(row)
```

**5. Run time-model-agent.**
Rebuild `memory/time_model/model.json` from all accumulated manual_log.csv data:
```python
# Compute median per task_type across all historical entries
# Update confidence levels based on sample count
# Write updated model.json
```

**6. Check open failure captures.**
Scan `memory/LEARNING/FAILURES/` for any entries from this week.
Read their context.json files.

**7. Generate the weekly review.**

Format:
```
WEEKLY REVIEW — [date range]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SIGNAL SUMMARY
  Briefing ratings this week: [count] ratings, avg [X.X]
  Low-rating events: [count] ([brief descriptions])
  Time logged: [total hours across X sessions]

GOAL STATUS
  [For each active goal:]
  [GOAL NAME]
  Status: ON TRACK / DRIFTING / STALLED
  Evidence: [specific activity or lack thereof this week]
  Gap: [if drifting/stalled — what specifically hasn't moved]

PATTERNS THIS WEEK
  [Any recurring issue from signals or failures]

TIME MODEL UPDATES
  [Which task estimates were refined with new data]
  [New high-confidence estimates]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROPOSED CHANGES (requires /approve)
  [Any proposed updates to ACTIVE_GOALS.md, PLAN.md files, or AI Steering Rules]
```

**8. Check promotion rule.**
Review full ERRORS.md + ratings.jsonl history (not just this week).
If any pattern qualifies (rating ≤3, ≥3 occurrences, ≥2 tasks, 30 days):
Write the proposed rule to `.learnings/PENDING_RULES.md`.
Note at end of review: "1 steering rule promotion pending — run /approve to review."

**9. Write proposed changes to pending files.**
Do NOT write directly to ACTIVE_GOALS.md, PLAN.md, or AI_STEERING_RULES.md.
Stage all changes as `.proposed.md` files or in `.learnings/PENDING_*.md`.
Spencer approves via `/approve`.

---

## TONE
Direct. Data-sourced. No inflation of progress, no minimization of gaps.
"ACT math: 0 sessions this week. Third consecutive week. Test is 6 weeks out."
Not: "You might want to consider returning to ACT prep when you get a chance."
