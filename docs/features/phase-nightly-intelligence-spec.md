# JADE — Phase N.2: Nightly Intelligence Upgrade
**Spec status:** Ready for Claude Code execution  
**Depends on:** Phase 2.5 (Notion task layer), Phase 2.6 (Notion project engine)  
**Files touched:** `jade_nightly.py`, `jade_prompts.py`  
**New files:** None

---

## 1. Problem Statement

The current nightly check-in captures project state (next action, where I am, blockers) but does nothing with it. It logs inputs and moves on. Tonight's session on WTT Social Media Automation is a perfect example of the failure mode: Spencer described his project status in detail, Jade logged it, and produced nothing actionable.

The nightly should do what the weekly breakdown already does: take what it knows — project scope, remaining work, blockers, GCal free time — and produce a **concrete daily schedule** for that project on the spot.

---

## 2. Desired Behavior (Reference Example)

After Spencer updates a project during the nightly, Jade should produce output like this:

```
WTT Social Media Automation — 3 days remaining
Blocker: Chase approval on mega doc + subscription sign-off (not scheduled)

Unblocked work available now:
  Mon Apr 14   90m   Begin N8N workflow (Deep Work)
  Tue Apr 15   90m   Build automation flows (Deep Work)
  Wed Apr 16  120m   Finalize + polish deliverable (Deliverable)

Blocked tasks held:
  Subscription setup — waiting on Chase approval
  Mega doc sign-off — waiting on Chase

Add these to Notion? [yes / skip]
```

Key qualities: tight, informative, no conversational filler, blocker-aware, immediately actionable.

---

## 3. What Changes

### 3a. Project Check-In Block (existing flow)

The current check-in already collects:
- Next action
- Where I am
- Blockers

**No change to the questions.** The intelligence is applied *after* the answers are collected, not during.

### 3b. New: Post-Check-In Planning Block

After each project's check-in responses are captured, Jade runs a structured planning pass. This is a **second Haiku call** (same pattern as the post-session extraction call) that takes:

**Inputs:**
- Project name, next action, current status, blockers (from check-in)
- Project tasks from Notion (`get_project_tasks(project_id)`) — names, durations, energy type, statuses
- GCal free time for the next 7 days (`get_free_windows(days=7)`) — gaps after hard blocks
- Fixed constraints: school 8:15am–3pm weekdays, lacrosse 4:30–7pm in-season (pulled from GCal only — no hardcoded rules)
- Today's date

**Output (structured JSON from Haiku):**
```json
{
  "project_name": "WTT Social Media Automation",
  "total_remaining_mins": 300,
  "days_to_completion": 3,
  "blocker_summary": "Chase approval on mega doc + subscription sign-off",
  "blocked_tasks": ["Subscription setup", "Mega doc sign-off"],
  "schedule": [
    {
      "date": "2026-04-14",
      "label": "Mon Apr 14",
      "task": "Begin N8N workflow",
      "duration_mins": 90,
      "energy": "Deep Work"
    },
    {
      "date": "2026-04-15",
      "label": "Tue Apr 15",
      "task": "Build automation flows",
      "duration_mins": 90,
      "energy": "Deep Work"
    },
    {
      "date": "2026-04-16",
      "label": "Wed Apr 16",
      "task": "Finalize + polish deliverable",
      "duration_mins": 120,
      "energy": "Deliverable"
    }
  ],
  "notion_candidates": [
    {"task": "Begin N8N workflow", "date": "2026-04-14", "duration_mins": 90, "energy": "Deep Work"},
    {"task": "Build automation flows", "date": "2026-04-15", "duration_mins": 90, "energy": "Deep Work"},
    {"task": "Finalize + polish deliverable", "date": "2026-04-16", "duration_mins": 120, "energy": "Deliverable"}
  ]
}
```

### 3c. Terminal Output Format

Jade prints the breakdown immediately after the project check-in, before moving to the next project or closing:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  WTT Social Media Automation — 3 days · 300m remaining
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ⚠  Blocker: Chase approval on mega doc + subscription sign-off

  Schedule (unblocked):
  Mon Apr 14   90m   Begin N8N workflow            [Deep Work]
  Tue Apr 15   90m   Build automation flows         [Deep Work]
  Wed Apr 16  120m   Finalize + polish deliverable  [Deliverable]

  Held (blocked):
  — Subscription setup
  — Mega doc sign-off
```

Rules:
- No preamble, no "Here's what I'm thinking", no questions mid-block
- Blocker section only renders if blockers exist
- Held section only renders if blocked tasks exist
- Duration header shows total remaining + days-to-completion
- Energy type right-aligned in brackets

### 3d. End-of-Session Notion Prompt

After ALL projects have been checked in and ALL breakdowns have been shown, a single Notion prompt fires at the very end of the session (before "Good night"):

```
Add tasks to Notion?
  1  WTT Social Media Automation  (3 tasks · Mon–Wed)
  2  [Next project if applicable]
  all / none / 1,2

> 
```

- If Spencer types `all`, `1`, `2`, or a comma-separated list: launch `jade_ingest` for the selected projects
- If `none` or enter: skip, close normally
- `jade_ingest` is called via subprocess the same way `jade_timeblock.py` is called post-nightly — it receives the `notion_candidates` JSON as input

**If no projects had breakdowns generated** (e.g. everything was blocked or Spencer skipped all projects), the Notion prompt does not appear.

---

## 4. Scheduling Logic for the Haiku Call

The planning prompt instructs Haiku to:

1. Read the task list for the project (names, durations, energy types, statuses)
2. Filter to only `Not Started` and `In Progress` tasks
3. Identify which tasks are blocked based on Spencer's blocker response (keyword match + reasoning)
4. For unblocked tasks: fit them into free GCal windows across the next 7 days, respecting:
   - Deep Work tasks → morning windows preferred (before noon)
   - Light tasks → afternoon windows acceptable
   - Max 3h of project work per day (leave room for other commitments)
   - Don't schedule past the project deadline if one exists in Notion
5. Return the structured JSON — no prose, no filler

The planning system prompt is added to `jade_prompts.py` as `build_project_planning_prompt(project_data, free_windows, today)`.

---

## 5. New Function Required in `integrations/gcal.py`

```python
def get_free_windows(days=7, min_gap_mins=30):
    """
    Returns list of free windows across the next N days.
    Each window: {"date": "YYYY-MM-DD", "start": "HH:MM", "end": "HH:MM", "duration_mins": int}
    Gaps < min_gap_mins are excluded.
    """
```

This function already partially exists (the timeblock spec designed it). If it was built in Phase 2 (timeblock), import it. If not, build it now — same logic.

---

## 6. New Function Required in `integrations/jade_notion.py`

```python
def get_project_tasks(project_id):
    """
    Returns all tasks linked to a given project_id.
    Filters to Not Started + In Progress only.
    Returns list of: {name, duration_mins, energy, status, due_date}
    """
```

---

## 7. `jade_prompts.py` Addition

```python
def build_project_planning_prompt(project_name, next_action, status, blockers, tasks, free_windows, today):
    """
    Returns a system + user message pair for the planning Haiku call.
    System prompt: instructs model to return only valid JSON, no prose.
    User message: structured dump of project state + calendar windows.
    """
```

The system prompt for this call must be strict: "Return only valid JSON. No explanation. No preamble. No markdown fences." Same pattern as the post-session extraction call.

---

## 8. `jade_nightly.py` Changes

### In the project check-in loop (after all three fields are collected per project):

```python
# After collecting next_action, status, blockers for a project:
tasks = get_project_tasks(project['notion_id'])
free_windows = get_free_windows(days=7)
planning_json = run_planning_call(project_name, next_action, status, blockers, tasks, free_windows, today)
print_project_breakdown(planning_json)  # formats and prints the breakdown block
session_state['project_breakdowns'].append(planning_json)  # accumulate for end-of-session Notion prompt
```

### At end of session (before close):

```python
# After all projects processed, before Phase E close:
if session_state['project_breakdowns']:
    prompt_notion_ingest(session_state['project_breakdowns'])
```

---

## 9. Failure Handling

| Scenario | Behavior |
|---|---|
| `get_project_tasks()` returns empty | Skip breakdown, print: `  No tasks found in Notion for this project.` |
| `get_free_windows()` returns empty | Skip scheduling, print: `  No free windows found in next 7 days — schedule manually.` |
| Planning Haiku call fails / returns invalid JSON | Skip breakdown silently, log error to stderr, session continues normally |
| Project has no Notion ID linked | Skip breakdown entirely — only works for projects tracked in Notion |
| All tasks blocked | Print breakdown with only the "Held (blocked)" section — no schedule section |

---

## 10. ISC (Implementation Success Criteria)

1. After entering a project's next action / status / blockers, a breakdown renders immediately in the terminal — no extra prompts required
2. Breakdown correctly identifies blocked vs. unblocked tasks based on Spencer's blocker text
3. Schedule slots tasks into real GCal free windows — not fake times
4. End-of-session Notion prompt appears only when at least one project had a breakdown
5. Selecting a project at the Notion prompt launches `jade_ingest` with the correct task payload
6. Session length does not increase significantly — the planning call adds <3 seconds
7. If Notion has no tasks for a project, the check-in still completes normally

---

## 11. What Does NOT Change

- The three check-in questions (next action, where I am, blockers) — unchanged
- The nightly log format — unchanged  
- `tomorrow_context.json` — unchanged
- The overall session flow (Phase A through E) — unchanged
- The "Block tomorrow?" prompt at the end — remove it. The Notion ingest prompt replaces it.

---

## 12. Build Order

1. Add `get_free_windows()` to `gcal.py` (or verify it exists from Phase 2)
2. Add `get_project_tasks()` to `jade_notion.py`
3. Add `build_project_planning_prompt()` to `jade_prompts.py`
4. Add `run_planning_call()` and `print_project_breakdown()` to `jade_nightly.py`
5. Add `prompt_notion_ingest()` to `jade_nightly.py`
6. Remove "Block tomorrow?" prompt
7. Verify ISC 1–7

Run a full nightly session manually after each step. Don't batch them.
# Phase N.2 Addendum — Task Completion Tracking + Plan Auto-Adjustment

Append this to `docs/features/phase-nightly-intelligence-spec.md` before Claude Code begins execution.

---

## A1. What Changes

The nightly check-in already pulls today's Notion tasks via `get_todays_tasks()`. This addendum adds:

1. **Completion check** — for each task scheduled for today, Jade asks if it was done
2. **Partial completion handling** — Spencer can report how much was completed
3. **Auto-adjustment** — the remaining duration is recalculated and fed into the planning call, which rebuilds the schedule from the updated state

---

## A2. Completion Check Flow

After the project check-in questions (next action / where I am / blockers), and **before** the planning call fires, Jade runs a completion check for any tasks that were scheduled for today under that project.

### If tasks were scheduled for today under this project:

```
Tasks due today for WTT Social Media Automation:
  ✓ / % / ✗   Begin N8N workflow  (90m scheduled)
> 
```

Spencer responds in natural language. Jade interprets:

| Spencer types | Interpretation |
|---|---|
| `done` / `yes` / `✓` / `finished` | 100% complete → mark Done in Notion |
| `50%` / `half` / `45m` / `halfway` | Partial → calculate remaining, keep In Progress |
| `no` / `didn't get to it` / `✗` | 0% complete → stays Not Started, full duration carries forward |
| `mostly` / `almost` / `80%` | Partial → Jade infers ~80%, asks to confirm or correct |

One line per task. If multiple tasks were due today for the same project, Jade lists them together — not one prompt per task.

### If no tasks were scheduled today under this project:

Skip the completion check entirely. Go straight to the planning call.

---

## A3. Remaining Duration Calculation

After completion responses are collected:

```python
def calculate_remaining(task, completion_response):
    """
    Returns remaining_mins for a task given Spencer's natural language response.
    - "done" → 0
    - "50%" → task.duration_mins * 0.5
    - "45m" → task.duration_mins - 45
    - "no" → task.duration_mins (unchanged)
    Clamps to 0 minimum. Rounds to nearest 5 mins.
    """
```

The updated remaining durations are passed into the planning call instead of the original task durations. The schedule rebuilds automatically from where things actually stand — not from the original estimate.

---

## A4. Notion Updates (Silent, Immediate)

When completion is reported:

- `done` → call `update_task_status(task_id, "Done")` immediately, no prompt
- Partial → call `update_task_status(task_id, "In Progress")` + update `Estimated Duration` field to remaining mins
- `no` → no Notion update (status stays as-is, duration unchanged)

These writes happen silently before the planning call. Spencer does not see a confirmation — the update just happens.

---

## A5. Updated Terminal Output

The breakdown block gains a completion summary line when tasks were checked:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  WTT Social Media Automation — 3 days · 255m remaining
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Today: N8N workflow — 45m done, 45m carried forward

  ⚠  Blocker: Chase approval on mega doc + subscription sign-off

  Schedule (adjusted):
  Mon Apr 14   45m   N8N workflow (remainder)       [Deep Work]
  Tue Apr 15   90m   Build automation flows          [Deep Work]
  Wed Apr 16  120m   Finalize + polish deliverable   [Deliverable]

  Held (blocked):
  — Subscription setup
  — Mega doc sign-off
```

The "Today:" line only renders if at least one task was partially or fully completed today. "Carried forward" shows the remaining chunk that rolled into tomorrow's slot.

---

## A6. Tasks With No Project Link

Some tasks in Notion aren't linked to a project (standalone tasks). These still get a completion check — but outside the project loop, as a separate lightweight pass at the start of the session.

```
Tasks due today (standalone):
  Bio — significance of results (35m)   done / skip?
> 
```

- One prompt for all standalone tasks combined — not per-task
- Spencer types task names or numbers: `bio done`, `all done`, `skip`
- Jade updates Notion statuses silently
- No planning call fires for standalone tasks — they're one-offs, not part of a schedule

---

## A7. Updated Build Order

Insert these steps before the existing build order (Section 12 of main spec):

1. Add `calculate_remaining(task, response)` utility to `jade_nightly.py`
2. Add completion check pass for standalone tasks at session start (before project loop)
3. Add per-project completion check inside project loop, before planning call
4. Wire completion results into planning call inputs
5. Add silent Notion status + duration updates on completion report
6. Update `print_project_breakdown()` to render "Today:" line when applicable

Then continue with the original build order (get_free_windows, get_project_tasks, etc.).

---

## A8. Addendum ISC

8. Jade asks about today's scheduled tasks before generating the breakdown — not after
9. Partial completion correctly reduces remaining duration and shifts the schedule forward
10. Notion task statuses are updated silently during the session — no extra confirmation prompt
11. A fully completed task does not appear in the new schedule
12. Standalone tasks get a single grouped completion check at session start
