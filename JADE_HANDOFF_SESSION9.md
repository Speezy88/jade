# JADE — Session 9 Handoff
*Date: 2026-04-10 | Branch: main | Phases: Nightly Exit Fix + jade_setup.py + Phase 2.5 — Notion Task Layer*

---

## SESSION SUMMARY

Session 9 completed three things: (1) nightly exit path hardening (sentinel protocol + inactivity
timeout), (2) `jade_setup.py` — one-time Notion workspace setup, (3) Phase 2.5 — Notion Task Layer
in full. All committed and operational.

**Commits this session:**
```
9edc9dc  feat: phase 2.5 complete — notion task layer + jade_setup.py
1249f74  docs: sync documentation after phase 2.5
```

---

## WHAT WAS BUILT

### Nightly Exit Hardening (jade_nightly.py + jade_prompts.py)

Three-part fix for the nightly check-in having no clean exit path:

- **`[SESSION_COMPLETE]` sentinel:** Jade appends it after Phase E delivery and on detecting
  close signals ("stop", "done", "bye", etc.). The `jade()` print function strips it before
  display. Every `chat()` call is followed by `if _SENTINEL in response: sys.exit(0)`.
- **Post-Phase-E ack turn:** After Phase E, wait for Spencer's ack, send one more turn,
  then exit. Prevents abrupt termination mid-conversation.
- **10-minute inactivity timeout:** `signal.SIGALRM` fires `_timeout_handler` if no input
  for 600s. Disabled (`signal.alarm(0)`) before the extraction API call.
- **`_NIGHTLY_CLOSE_PROTOCOL`:** New constant in `jade_prompts.py`. Injected into nightly
  system prompt. Instructs Jade on the sentinel and exit-intent keywords.

### jade_setup.py (new — one-time Notion workspace setup)

Creates all 6 Notion databases in dependency order via the Notion API. Run once before Phase 2.5;
not called at runtime.

Key design decisions:

- **urllib only — never requests:** `requests` returns 401 on valid Notion API keys on this
  machine. All HTTP via `urllib` + `ssl._create_unverified_context()`.
- **`_extract_notion_id(value)`:** Normalizes full Notion URLs, bare hex IDs (32-char no
  dashes), and UUID format to canonical UUID. Handles Spencer pasting the full page URL
  from the browser.
- **Credentials from `~/.config/jade/credentials`:** Same file as GCal. KEY=VALUE format.
  Keys: `NOTION_API_KEY`, `NOTION_PARENT_PAGE_ID`.
- **Creation order (dependency-driven):**
  1. Projects (no relations)
  2. Tasks → Projects
  3. Research Vault → Projects
  4. Skills → Projects, Research Vault
  5. Practice Log → Skills
  6. Opportunities → Skills
- **`--check` mode:** Validates each DB accessible AND validates that each relation property
  points to the correct target DB ID (cross-checks against `notion_ids.json`). Catches stale
  IDs after `--force` re-runs.
- **Output:** Prints full Notion URLs for each created DB. Writes all IDs to
  `memory/notion_ids.json`.

### integrations/jade_notion.py (new — Notion task layer)

Task queries and writes for the Notion Tasks DB. All functions catch all exceptions and
return safe defaults — never raises.

- **`_load_config()`** → `(api_key, ids_dict)` from credentials + notion_ids.json
- **`_SSL_CTX`** = `ssl._create_unverified_context()` — passed to every `urlopen()`
- **Query functions:**
  - `get_todays_tasks()` — filter: due = today + active status; sorted by priority rank then due time
  - `get_upcoming_tasks(n=7)` — after today through n days
  - `get_overdue_tasks()` — before today + active
  - All return `list[dict]` with schema: `{id, name, priority, due, energy, duration, status, area, recurring, chunk_size, total_target, rec_start, rec_end}`
- **Priority sort rank:** `{"🔴 High": 0, "🟡 Medium": 1, "🟢 Low": 2}`
- **Pagination:** `_query_tasks()` handles `has_more` + `start_cursor` loop
- **Write functions:**
  - `update_task_status(task_id, status)` → bool
  - `create_task(name, area, priority, ...)` → page_id or None
  - `create_recurring_task(name, area, priority, total_target, chunk_size, start_date, ...)`:
    - `num_instances = math.ceil(total_target / chunk_size)`
    - `end_date = start_date + timedelta(days=num_instances - 1)`
    - Creates parent task + N child tasks named "Task Name — Day 1/12"
    - Returns list of page IDs (parent first)

### jade_briefing.py + jade_nightly.py (updated)

Both wired with `get_todays_tasks()` and `get_overdue_tasks()`. Injected into context so Jade
references tasks by name during briefing and nightly check-in.

### jade_prompts.py (updated)

- Added `_PRIORITY_LABEL` dict and `_format_task_line(task)` helper
- Updated `_format_context()` to render `tasks_today` and `tasks_overdue` in briefing prompt
- Updated `_format_nightly_context()` to inject tasks for by-name reference during check-in
- Added `_NIGHTLY_CLOSE_PROTOCOL` constant + wired into `build_nightly_system_prompt()`

---

## GOTCHAS ESTABLISHED THIS SESSION

### requests returns 401 on valid Notion API keys on this machine
Use `urllib` + `ssl._create_unverified_context()` for ALL Notion API calls. This applies to
`jade_notion.py`, `jade_setup.py`, and any future files that touch Notion (e.g., `jade_research.py`
in Phase 2.7). Never use `requests` for Notion calls.

### Notion API token format
Newer Notion integration tokens use `ntn_...` format (no `secret_` prefix).

### NOTION_PARENT_PAGE_ID format
Spencer will often paste the full URL. `_extract_notion_id()` handles all formats. Follow
this pattern in any future code reading that value.

---

## ISC STATUS — PHASE 2.5

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| ISC-1 | `jade_notion.py` imports cleanly | ✅ Code verified | |
| ISC-2 | `get_todays_tasks()` returns sorted task dicts | ⚠ Code verified | Requires tasks in DB |
| ISC-3 | `get_overdue_tasks()` returns tasks past due date | ⚠ Code verified | Requires tasks in DB |
| ISC-4 | `create_task()` creates a page in Tasks DB | ⚠ Code verified | Requires Notion write |
| ISC-5 | `create_recurring_task()` creates parent + N children | ⚠ Code verified | Requires Notion write |
| ISC-6 | Briefing injects `tasks_today` + `tasks_overdue` | ✅ Code verified | Wired |
| ISC-7 | Nightly check-in references tasks by name | ✅ Code verified | Wired |
| ISC-8 | `[SESSION_COMPLETE]` sentinel exits nightly cleanly | ✅ Verified | Tested in session |
| ISC-9 | 10-min inactivity timeout fires `sys.exit(0)` | ✅ Code verified | Logic verified |
| ISC-10 | `jade_setup.py --check` validates DB accessibility | ✅ Verified | All 6 DBs passed |
| ISC-11 | `jade_setup.py --check` validates relation targets | ✅ Verified | All relations correct |
| ISC-12 | `memory/notion_ids.json` written with all 6 DB IDs | ✅ Verified | File present |

---

## NOTION DB IDs

```json
{
  "projects_db_id":     "33ee0769-3060-812d-ad92-db4243ae7bc6",
  "tasks_db_id":        "33ee0769-3060-818a-88a8-e0748ff5220d",
  "research_db_id":     "33ee0769-3060-81e9-bfd6-dd1183c25040",
  "skills_db_id":       "33ee0769-3060-8136-bef7-d1f61dc693ba",
  "practice_log_db_id": "33ee0769-3060-8118-8021-ee097e9fa46e",
  "opportunities_db_id":"33ee0769-3060-8145-8299-fdcb2ca7d1f5"
}
```

---

## EXACT NEXT STEPS TO RESUME

### Phase 2.6: Notion Project Engine

Per `docs/PROJECT_STATUS.md` and `docs/features/Jade_Phase_2.5-2.7_Spec.md`:

1. **Add to `integrations/jade_notion.py`:**
   - `create_project(name, one_line_goal, area, deadline, time_budget)` → page_id
   - `edit_project(project_id, **fields)` → bool
   - `update_next_action(project_id, next_action)` → bool
   - `get_active_projects()` → list[dict] sorted by deadline

2. **Wire into `jade_nightly.py`:**
   - Phase C discussion → offer to update next action on mentioned projects

3. **Wire into `jade_briefing.py`:**
   - Projects with deadline < 48 hours → flagged in briefing context

4. **ISC-7 through ISC-12 must all pass before moving to 2.7**

---

## KNOWN GAPS AT CLOSE

| Gap | Impact | Fix |
|-----|--------|-----|
| Phase 2.5 ISC-2 through ISC-7 code-verified only | No live task data during session | Verify once tasks exist in Notion DB |
| SSL workaround (`ssl._create_unverified_context()`) | Security advisory | Run `/Applications/Python\ 3.13/Install\ Certificates.command` |
| `.claude/hooks/` not implemented as Python files | `rating_capture`, `pre_tool_use` don't execute | Phase 3 |

---

*Handoff generated: 2026-04-10 | Session mode: FULL | Rating: 5*
