# /log
# Place at: ~/Jade/.claude/commands/log.md
# Usage: /log math 45  OR  /log "english essay draft" 70 "harder than expected"
# Tier 1 use — Spencer types this after completing any task

Quick time entry for the task duration model.
30 seconds to use. The data accumulates into personal estimates that make /timeblock accurate.

---

## ARGUMENT PARSING

Accepts flexible natural language. Parse the following from the input:
- **task_type** — what kind of work (math, essay, reading, problem_set, lab, research, etc.)
- **subject** — which class or project (optional: math, english, history, jade, internship)
- **duration_minutes** — how long it actually took
- **notes** — optional freeform note

Examples Jade must parse correctly:
- `/log math 45` → task_type=problem_set, subject=math, duration=45
- `/log english essay 70` → task_type=essay, subject=english, duration=70
- `/log "history reading" 25 "chapter was dense"` → task_type=reading, subject=history, duration=25, notes="chapter was dense"
- `/log jade 90` → task_type=coding, subject=jade, duration=90
- `/log internship meeting 30` → task_type=meeting, subject=internship, duration=30

If ambiguous, make a reasonable inference and show what was logged. Do not ask clarifying questions for minor ambiguity.

---

## EXECUTION

**1. Parse the entry.**

**2. Append to `memory/time_model/manual_log.csv`:**
```csv
date,task_type,subject,duration_minutes,notes
2026-03-04,problem_set,math,45,
2026-03-04,essay,english,70,harder than expected
```
If the file doesn't exist, create it with the header row first.

**3. Confirm the entry in one line:**
```
Logged: math problem set — 45 min  (running median: 52 min, 8 samples)
```
Show the updated running median if ≥3 samples exist for this task_type.

**4. If this entry is significantly different from the existing median (>40% off), note it:**
```
Logged: math problem set — 90 min  (median is 52 min — notably longer. Note anything unusual?)
```
This surfaces outliers that might indicate a particularly hard assignment vs. a typical session.

**5. Do not lecture about time management.** Log and confirm. That's it.

---

## TIME MODEL UPDATE

The time model (`memory/time_model/model.json`) is rebuilt weekly by the `time-model-agent`
during `/goal-review`. Manual log entries feed that rebuild.

The model uses median (not mean) to resist outlier distortion.
Confidence levels: low (<3 samples), medium (3–7), high (8+).
