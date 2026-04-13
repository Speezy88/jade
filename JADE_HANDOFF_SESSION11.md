# JADE — Session 11 Handoff
*Date: 2026-04-12 | Branch: main | Phase: 2.6 in progress*

---

## SESSION SUMMARY

Session 11 built Phase 2.6 (Notion Project Engine) and jade_ingest v2 (5 destination
types). All code is committed. Documentation is synced. Two things are unresolved:
ISC-I9 has a confirmed bug, and ISC-8 through ISC-12 + ISC-I10 through I17 have not
been run.

**Commits this session:**
```
2fb6802  feat: jade_ingest v2 — 5 destination types, date inference, project linking
628d397  docs: sync documentation after phase 2.6 + jade_ingest v2
```

**Uncommitted at handoff:** None. Working tree is clean except for cache/runtime files
(`memory/cache/`, `memory/LEARNING/SIGNALS/ratings.jsonl`).

---

## WHAT WAS BUILT

### Phase 2.6 — Notion Project Engine

**`integrations/jade_notion.py` — 7 new functions:**

```python
# Helpers
_page_to_project(page)          # raw Notion page → {id, name, goal, area, status, deadline, url}
_orientation_blocks(...)        # builds ⚡/📍/🚧 block list for page body

# Project queries
get_active_projects(area=None)  # queries projects_db_id, filter Status=🔄 Active

# Project writes
create_project(name, goal, area, why, deadline, deadline_type, time_budget, notes)
    # raises ValueError if name/goal/area missing (ISC-7)
    # writes orientation block as page body via children= in POST payload (ISC-9)
    # returns page_id or None

edit_project(project_id, updates: dict)
    # PATCH only the fields in updates — never touches others (ISC-10)
    # supported keys: status, goal, why, deadline, deadline_type, time_budget

update_next_action(project_id, next_action, where_i_am, blockers=None)
    # appends dated block via PATCH /blocks/{page_id}/children

# Ingest v2 functions
append_page_content(page_id, content)
    # appends: divider + heading_3 "Note — YYYY-MM-DD HH:MM" + paragraph
    # same blocks-append endpoint as update_next_action

create_research_job(query, area, project_id=None)
    # POST to research_db_id; Status=Draft

create_practice_entry(skill, duration_mins, entry_date, notes=None)
    # POST to practice_log_db_id; Skill relation OMITTED (Phase 2.8)
    # Entry Title = "{skill} — {date}"
```

**`jade_nightly.py` — Part 2 implemented:**
Between task closeout (Part 1) and tomorrow flag (Part 3). Calls `get_active_projects()`,
loops per project: `"Next action? [skip / text]:"` → if answered, prompts where/blockers
→ calls `update_next_action()`. Skipped projects don't write anything. Pure input/print,
no LLM, consistent with Part 1 pattern.

**`jade_briefing.py` — `projects_urgent` deadline flag (ISC-12):**
After task fetch, calls `get_active_projects()`. Filters: `deadline ≤ today + 48 hours`.
Result → `projects_urgent` list → passed into `build_system_prompt()` context.

**`jade_prompts.py` — `projects_urgent` rendering:**
In `_format_context()`: if `projects_urgent` non-empty, appends "⚠️ Projects due within
48 hours:" section before the missed_nightly check.

### jade_ingest v2 — 5 destination types

Full rewrite. Same UX: paste → preview → confirm → write. Classification is now a
runtime-built prompt (`_build_classify_prompt(today, project_names)`) that injects:
- Today's date — enables natural-language date resolution
- Active project names — enables project linking by name match

**New destination types vs v1:**

| Type | Destination | Trigger keywords |
|------|-------------|-----------------|
| task | Tasks DB | action item, to-do |
| project | Projects DB | named initiative with goal |
| research | Research Vault (Status=Draft) | "look into", "understand X", question |
| practice | Practice Log | "did X min of Y", explicit duration |
| note | Existing project page body | freeform idea tied to a project |

**Priority format change:** Classification now returns `"High"` / `"Medium"` / `"Low"`.
`_PRIORITY_MAP` in the script converts to emoji strings before calling `create_task()`.

**`confirm_and_edit()` — updated for 5 types.** Field sets per type:
- task: name, area, priority, due_date, duration_mins, linked_project
- project: name, goal, area, why
- research: query, area, linked_project
- practice: skill, duration_mins, date, notes
- note: content, linked_project

**Area mapping — resolved discrepancies from spec:**
- "Lacrosse" is not a valid Notion area → maps to "Personal Goals"
- "Manatee" → "Manatee Aquatic" (consistent with existing data, not "Side Projects/Business")

---

## OPEN BUG: ISC-I9 — Note → Project Page Body

**Symptom:** When classifying a note, the write step falls back to "No matching project
— create as task instead?" instead of appending to the project page body.

**Root cause (unknown — debug next session):**

Three possible failure points, in order of likelihood:

**1. Project name mismatch in `project_map`** (most likely)
`project_map` is built from `get_active_projects()` which only returns projects with
`Status = 🔄 Active`. If the target project exists in Notion but has a different status
(Not Started, Done, etc.), it won't appear in the map. The name lookup returns `None`
and the fallback fires.

Diagnostic: Add a temporary `print(f"project_map: {list(project_map.keys())}")` at the
top of `run()` and check if the expected project name appears.

**2. Name case / punctuation mismatch**
Haiku might return the project name with slightly different casing or punctuation than
the Notion record (e.g. "Manatee" vs "Manatee Aquatic"). `project_map` is an exact
dict lookup — no fuzzy matching at write time.

Diagnostic: Print `rec.get("linked_project")` alongside `project_map.keys()` to compare.

**3. `append_page_content()` PATCH failure**
The Notion blocks-append endpoint (`PATCH /blocks/{page_id}/children`) works for
project pages (confirmed by `update_next_action()` in nightly). But the page_id must
be the raw UUID — if it contains dashes in a different format it may 404.

Diagnostic: Print the return value of `append_page_content()` and check stderr.

**Fix path once root cause identified:**
- If (1): either set test project to Active status, or add a fallback query for all
  projects regardless of status in `_load_projects()`
- If (2): normalize both sides before lookup (`.lower().strip()`)
- If (3): strip/normalize page_id before passing to `append_page_content()`

---

## EXACT NEXT STEPS TO RESUME

### 1. Debug ISC-I9 (start here)

```bash
# Quick diagnostic — add this temporarily to run() after project_map is loaded:
# print(f"[debug] project_map keys: {list(project_map.keys())}")

python3 jade_ingest.py
# Input: "Idea for [exact project name] — [some content]"
# Watch: does the project name appear in debug output?
#        does "No matching project" appear or does it write?
```

### 2. Run ISC verification table

After ISC-I9 is fixed, run each manually:

**Phase 2.6 ISC:**

| ISC | Test | Expected |
|-----|------|----------|
| ISC-7 | `python3 -c "from integrations.jade_notion import create_project; create_project('X', None, 'Personal Goals')"` | `ValueError: goal` |
| ISC-8 | Create project with all optional fields → check Notion page | All 8 settable fields populated |
| ISC-9 | Open newly created project in Notion | ⚡/📍/🚧 block at top of page body |
| ISC-10 | `edit_project(id, {"status": "🔄 Active"})` → check Notion | Only Status changed |
| ISC-11 | `python3 jade_nightly.py --now` → enter next action for active project | Dated update block appended in Notion |
| ISC-12 | Set a project deadline to tomorrow → `python3 jade_briefing.py` | Deadline flagged in briefing output |

**jade_ingest v2 ISC:**

| ISC | Input | Expected |
|-----|-------|----------|
| ISC-I8 ✅ | "Finish the WTT pitch by Friday" | task, area=Wellbeing Think Tank, due_date=next Friday |
| ISC-I9 ❌ | "Idea for [project] — [content]" | note → project page body, timestamped, verbatim |
| ISC-I10 | "Look into how ACT science questions are structured" | research record in Research Vault |
| ISC-I11 | "Did 45 minutes of ACT math practice" | practice entry, skill=ACT Math, duration=45 |
| ISC-I12 | Task mentioning an active project by name | Linked Project field set in Notion |
| ISC-I13 | Mixed 5-type paste (see spec) | All 5 classified, preview shows all before confirm |
| ISC-I14 | "finish essay next week" | due_date = next Monday's date (not hallucinated) |
| ISC-I15 | Note with no matching project | "No matching project — create as task? y/n" prompt |
| ISC-I16 | Any ingest run | project_map fetched once, not per-record |
| ISC-I17 | 10+ mixed records in one paste | No crash, all processed |

### 3. After all ISC pass

```bash
# Close Phase 2.6
git add -A
git commit -m "feat: phase 2.6 complete — ISC-7 through ISC-12 verified"

# Move to Phase 2.7
# Spec: docs/features/Jade_Phase_2.5-2.7_Spec.md (Phase 2.7 section)
# New file: jade_research.py
# New DB already exists: research_db_id in notion_ids.json
```

---

## FILE STATE AT HANDOFF

```
integrations/jade_notion.py  — 650+ lines; 7 new functions added this session
jade_ingest.py               — 495 lines; full v2 rewrite; committed 2fb6802
jade_nightly.py              — Part 2 implemented between lines ~125–152
jade_briefing.py             — projects_urgent added ~lines 124–130
jade_prompts.py              — projects_urgent in _format_context()
```

---

## KNOWN GOTCHAS

| Gotcha | Detail |
|--------|--------|
| Practice Log Skill relation | `create_practice_entry()` leaves Skill field blank. Entry Title includes skill name for manual linking. Phase 2.8 fix. |
| get_active_projects() filter | Only returns Status=🔄 Active. Projects in other statuses won't appear in project_map or nightly Part 2. |
| Notion blocks API for page content | `update_next_action()` and `append_page_content()` both use `PATCH /blocks/{page_id}/children` — appends only. Cannot insert at top or replace existing blocks without fetching block IDs first. |
| ISC-I9 bug | See Open Bug section above. |

---

*Handoff generated: 2026-04-12 | Session mode: FULL | Rating: pending*
