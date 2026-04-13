# JADE — Session 10 Handoff
*Date: 2026-04-11 | Branch: main | Phase: 2.5 close / 2.6 boundary*

---

## SESSION SUMMARY

Session 10 completed four things: (1) nightly redesign — full rewrite from 12-minute
conversational LLM session to 2–3 minute pure script, (2) Notion data source priority
enforcement across jade_briefing.py + jade_prompts.py, (3) jade_ingest.py — new bulk
ingest command, (4) field rename in jade_notion.py ("Estimated Duration" → "Estimated
Duration (min)").

**Commits this session:**
```
5f89693  docs: sync documentation after nightly redesign + jade_ingest.py
```

**Still uncommitted at handoff:**
```
M  .claude/commands/brief.md
M  AI_STEERING_RULES.md
M  CLAUDE.md
M  SOUL.md
M  docs/features/Jade_Phase_2.5-2.7_Spec.md
M  integrations/jade_notion.py
M  jade_briefing.py
M  jade_nightly.py
M  jade_prompts.py
M  jade_setup.py
M  memory/LEARNING/SIGNALS/ratings.jsonl
?? jade_ingest.py
```

---

## WHAT WAS BUILT

### Nightly redesign (jade_nightly.py — complete rewrite)

Rewrote from a 364-line, 5-phase conversational check-in (Haiku, multi-turn,
structured extraction) into a 140-line pure script with no LLM calls.

**New structure:**
- **Part 1 — Task closeout:** `get_todays_tasks()` → filter for incomplete statuses →
  one `input("  {task['name']}? yes/no: ")` per task → `update_task_status(task_id, "Done")`
  or `update_task_status(task_id, "Not Started")` immediately.
- **Part 3 — Tomorrow flag:** `get_upcoming_tasks(1)` → print names → one free-text
  `input("> ")` → write `tomorrow_context.json` + nightly log. Exits immediately.
- **Part 2 — Project Next Action:** DEFERRED to Phase 2.6. Requires `edit_project()` and
  `get_active_projects()` which don't exist yet.
- **Session timeout:** `signal.alarm(300)` — 5-minute overall timeout, disabled after
  final input.
- **Post-run:** Offers to trigger `jade_timeblock.py` (`subprocess.run()`).

**Removed from jade_nightly.py:**
- `import anthropic`, `jade_prompts`, `gcal` imports
- `_MODEL`, `_MAX_TOKENS`, `_SENTINEL`, `_EXTRACTION_SYSTEM` constants
- `select_domains()`, `load_recent_logs()`, `chat()`, `jade()`, `extract_structured()`,
  `_write_transcript_fallback()`, `ask()` functions

**jade_prompts.py:** `_format_nightly_context()` reduced to Phase 2.6 stub. No longer
called by `jade_nightly.py`. Context keys: `today`, `tasks_today`, `tasks_tmrw` only.
All old context fields (days_to_act, calendar_events, domains, recent_logs) removed.

**SOUL.md:** New NIGHTLY CHECK-IN SPECIFICATION section added documenting the 3-part
structure, what Jade does NOT do, and the Phase 2.6 deferral.

### Notion data source priority enforcement

**jade_briefing.py:** Added credentials guard before calling jade_notion.

```python
_notion_creds = Path.home() / ".config" / "jade" / "credentials"
_notion_ids   = Path("/Users/spencerhatch/Jade/memory/notion_ids.json")
if _notion_creds.exists() and _notion_ids.exists():
    tasks_today   = get_todays_tasks()
    tasks_overdue = get_overdue_tasks()
else:
    tasks_today   = None
    tasks_overdue = None
```

`None` (not `[]`) signals Notion unavailable. `[]` means healthy call, zero results.

**jade_prompts.py `_format_context()`:** Handles the distinction:
- `tasks_today is None` → "⚠️ Notion unavailable — task data missing."
- `tasks_today == []` → "Today's tasks: none in Notion today."
- `tasks_overdue is None` → silent (already reported under tasks_today None block)

**AI_STEERING_RULES.md:** New rule added — task data must come from jade_notion.py.
Never fabricate task names, due dates, or overdue items. If unavailable, state it.

**.claude/commands/brief.md:** Step 2 updated to include
`integrations.jade_notion.get_todays_tasks()` and `get_overdue_tasks()` alongside
gcal + schoology fetches.

### jade_ingest.py (new — bulk Notion ingest)

Standalone script. Not called by launchd. Usage: `python3 jade_ingest.py`.

**Flow:**
1. Multi-line paste input until blank line or EOF.
2. Single Haiku call (`_CLASSIFY_SYSTEM` prompt) → JSON with `tasks[]` + `projects[]`.
3. Preview printed: tasks with priority/area/due; projects marked "(skipped)" (Phase 2.6).
4. `input("Write to Notion? [yes / abort]: ")` → confirm or exit.
5. `create_task()` called per task → `✓ name` or `✗ name (write failed)`.
6. Summary: "N task(s) created, M project(s) skipped (Phase 2.6)."

**Classification prompt enforces exact Notion strings:**
- Valid areas: `"School/ACT/College Apps"`, `"Wellbeing Think Tank"`, `"Personal Goals"`,
  `"Side Projects/Business"`, `"Reading/Learning"`, `"Manatee Aquatic"`
- Valid priorities: `"🔴 High"`, `"🟡 Medium"`, `"🟢 Low"`
- Keyword hint: `"Manatee", "aquatic", "swim", "pool", "lifeguard"` → `"Manatee Aquatic"`
- Default area: `"Personal Goals"`. Default priority: `"🟡 Medium"`.

**ISC-I1 and I7 verified.** ISC-I2 through I6 require live Notion run.

### jade_setup.py — Manatee Aquatic area

Added `{"name": "Manatee Aquatic", "color": "pink"}` to `_AREA_OPTIONS`. Applied to all
6 DB schemas (Tasks, Projects, Research Vault, Skills, Practice Log, Opportunities).

**NOTE:** If the Notion workspace was created before this session, the existing DBs do NOT
have "Manatee Aquatic" as a select option. Run `jade_setup.py --force` to rebuild, or add
the option manually in Notion. `create_task()` will fail with a 400 if the area isn't in
the DB's allowed select options.

### jade_notion.py — field rename

`"Estimated Duration"` → `"Estimated Duration (min)"` on three lines:
- Line 144: `_page_to_task()` read
- Line 282: `create_task()` write
- Line 360: `create_recurring_task()` write

---

## GOTCHAS CARRIED FORWARD

### create_project() does not exist yet
Phase 2.6. `jade_ingest.py` shows projects in preview but skips writes. `jade_nightly.py`
Part 2 is commented out with a Phase 2.6 note. Do not call `create_project()` anywhere
until it's built.

### Manatee Aquatic area not in existing Notion DB
`jade_setup.py --force` will rebuild all DBs and pick up the new area. This wipes existing
data. Alternative: add the select option manually in Notion for each relevant DB.

### Estimated Duration (min) rename
If there are existing tasks in Notion with data in the old `"Estimated Duration"` property,
that data will no longer be read (wrong property name). The Notion property itself may need
renaming in the DB schema. Check via `jade_setup.py --check`.

### urllib + ssl._create_unverified_context() for all Notion calls
Inherited from Session 9. Never use `requests` for Notion API calls on this machine.

---

## ISC STATUS

### jade_ingest.py

| # | Criterion | Status |
|---|-----------|--------|
| I1 | `python3 jade_ingest.py` imports cleanly | ✅ Verified |
| I2 | 3-task paste → valid JSON preview with all 3 | ⚠ Needs live run |
| I3 | Preview shows name + priority + area + due | ⚠ Needs live run |
| I4 | "abort" → nothing written to Notion | ⚠ Needs live run |
| I5 | "yes" → create_task() called → ✓ lines printed | ⚠ Needs live run |
| I6 | Projects → shown as "skipped (Phase 2.6)" → not written | ⚠ Needs live run |
| I7 | Empty input → "Nothing entered. Exiting." | ✅ Verified |

### Phase 2.5 nightly redesign

| # | Criterion | Status |
|---|-----------|--------|
| N6 | Session completes in < 3 min (3 tasks) | ✅ Code verified |
| N7 | Task questions driven by Notion, not hardcoded | ✅ Code verified |
| N8 | "yes" → update_task_status() → next task immediately | ✅ Code verified |
| N9 | Project Next Action update | ⛔ Deferred to Phase 2.6 |
| N10 | Addition input → write → "Good night." → exit | ✅ Code verified |
| N11 | SOUL.md nightly spec matches implementation | ✅ Verified |

---

## EXACT NEXT STEPS TO RESUME

### Phase 2.6: Notion Project Engine

Per `docs/features/Jade_Phase_2.5-2.7_Spec.md`:

1. **Add to `integrations/jade_notion.py`:**
   - `create_project(name, one_line_goal, area, deadline, time_budget)` → page_id
   - `edit_project(project_id, **fields)` → bool
   - `update_next_action(project_id, next_action)` → bool
   - `get_active_projects()` → list[dict] sorted by deadline

2. **Wire into `jade_nightly.py` Part 2:**
   - For each active project mentioned in today's tasks: offer to update next action
   - Requires `edit_project()` to exist first

3. **Wire into `jade_briefing.py`:**
   - Projects with deadline < 48 hours → flagged in context

4. **ISC-7 through ISC-12 must all pass before moving to 2.7**

**Before starting:** Commit the uncommitted changes from Session 10 (listed above).

---

## KNOWN GAPS AT CLOSE

| Gap | Impact | Fix |
|-----|--------|-----|
| jade_ingest.py ISC-I2–I6 unverified | Needs live Notion run | Run once tasks exist |
| Manatee Aquatic not in existing Notion DB schemas | create_task() fails for that area | `--force` rebuild or manual Notion edit |
| No WORK/ directory or ISC.json for session features | ISC tracking skipped again | Create before Phase 2.6 build starts |
| SSL workaround (`ssl._create_unverified_context()`) | Security advisory | `/Applications/Python\ 3.13/Install\ Certificates.command` |

---

*Handoff generated: 2026-04-11 | Session mode: FULL | Rating: pending*
